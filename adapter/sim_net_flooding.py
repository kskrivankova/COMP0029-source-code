from cuttlefish.network_primitives.network import Network
from cuttlefish.packet_management import attr, INT

from random import random
import time

import _thread
import threading
import copy


# TODO implement automatic versioning
class NetworkFloodingSim(Network):
    """
        Network flooding - a generalised implementation of Trickle.

        Params:
        flagged attributes: attributes in the packet scheme to be tracked

            [dict] flagged_attributes = {
                    1: (0, 2),
                    3: (1, ),
                    ...
            }
        i_min: shortest possible transmission interval [milliseconds]
        i_max: longest possible transmission interval [milliseconds]
        consistent: attribute IDs match
    """

    def __init__(self, address, state, default_data, flagged_attributes, i_min, i_max, is_consistent_callback, update,
                 *args, redundancy_const=1, versioning=True, version_id_size=2, meta=None, buffer_size=10,
                 **kwargs):
        super().__init__(address, *args, meta=meta, buffer_size=buffer_size, **kwargs)

        self.last_flagged_data = None

        self.state = state   # State supplied which can be modified (not reassigned)
        self.default_data = default_data  # The default packet data sent

        self.flagged_attributes = flagged_attributes  # The parts of the packet which are observed for change
        self.I_MIN = i_min / 1000
        self.I_MAX = i_max / 1000
        self.REDUNDANCY_CONST = redundancy_const

        self.is_consistent_callback = is_consistent_callback  # Callback to test data consistency
        self.update = update  # Callback to update the default data

        self.interval_length = None
        self.transmit_time = None
        self.counter = None

        self.versioning = versioning
        self.version_id_size = version_id_size
        self.version_id_scheme = attr("version_id", version_id_size, type=INT)
        self.version_id = 0

        self.interval_alarm = None
        self.transmit_alarm = None

        self.cancel_flag = threading.Event()
        self.uplink_arg = None
        self.downlink_arg = None

        self.channel = None

    def init_connection(
        self,
        socket,
        channel_id,
        serializer,
        orchestrator,
        scheduler,
        *args,
        ack=False,
        ack_callback=None,
        identified=False,
        channel=None,
        mode=None,
        schedule_callback=None,
        recv_buffer_size=None,
        **kwargs
    ):
        super().init_connection(socket, channel_id, serializer, orchestrator, scheduler, *args, ack=ack,
                                ack_callback=ack_callback, identified=identified,
                                schedule_callback=self.scheduler_callback, recv_buffer_size=recv_buffer_size, **kwargs)

        self.channel = channel

        if self.versioning:
            serializer.add_layer(headers=[self.version_id_scheme])
            self.default_data.append([self.version_id])

        self.last_flagged_data = self.get_flagged_attributes(self.default_data)

    def process_recv(self, data, meta, *args, **kwargs):
        super().process_recv(data, meta, *args, **kwargs)

        if self.versioning:
            version_id = data.pop().pop()
        else:
            version_id = self.version_id

        flagged_attributes = self.get_flagged_attributes(data)

        if (self.is_consistent(flagged_attributes, meta=meta)) and (version_id == self.version_id):
            # print("CONSISTENT: {}".format(data[0]))
            self.counter += 1
        elif self.interval_length > self.I_MIN:
            # print("INCONSISTENT: {}, id: {}".format(data[0], version_id))

            if (version_id > self.version_id) or (not self.versioning):
                self.update_default_data([list(layer.values()) for layer in data], version_id, meta=meta)
                # print("Updated: {}".format(self.default_data, version_id))

            self.reset_interval()

    def disconnect(self):
        self.cancel_flag.set()

    def get_flagged_attributes(self, data):
        attributes = []

        for position in self.flagged_attributes.items():
            layer_i = position[0]
            attr_indices = position[1]
            for attr_i in attr_indices:
                attr_data = data[layer_i][attr_i]
                attributes.append(attr_data)

        return attributes

    def is_consistent(self, received_flagged_attributes, meta=None):
        return self.is_consistent_callback(self.state,
                                           received_flagged_attributes,
                                           self.last_flagged_data,
                                           meta
                                           )

    def update_default_data(self, new_data, version_id=None, meta=None):
        if self.versioning:
            self.default_data.pop()  # Remove version id layer

        self.default_data = self.update(self.state, self.default_data, new_data, meta)
        self.last_flagged_data = self.get_flagged_attributes(new_data)

        if version_id:
            self.version_id = version_id
            self.default_data.append([self.version_id])
        elif self.versioning:
            self.version_id += 1
            self.default_data.append([self.version_id])

    def scheduler_callback(self, *args, **kwargs):
        def listen():
            while True:
                scheduler.downlink(self.downlink_arg)
                time.sleep(0.01)

        scheduler = args[0]
        args = list(args)
        args.append(kwargs)

        self.downlink_arg = (args[0], kwargs)
        self.uplink_arg = (args[0], args[1], kwargs)

        self.start_interval()

        _thread.start_new_thread(listen, tuple())

    def start_interval(self):
        delta_i = self.I_MAX - self.I_MIN
        self.interval_length = self.I_MIN + delta_i * random()

        self.reset_primitives()

    def restart_interval(self):
        new_interval_length = self.interval_length * 2

        if new_interval_length > self.I_MAX:
            self.interval_length = self.I_MAX
        else:
            self.interval_length = new_interval_length

        self.reset_primitives()

    def reset_interval(self):
        self.cancel_flag.set()

        self.interval_length = self.I_MIN

        self.reset_primitives()

    def reset_primitives(self):
        half_interval = self.interval_length / 2
        self.transmit_time = half_interval + (half_interval * random())

        self.counter = 0
        self.cancel_flag.clear()

        self.transmit_alarm = self.set_alarm(self.uplink, self.transmit_time, periodic=False, debug="transmit")
        self.interval_alarm = self.set_alarm(self.restart_interval, self.interval_length, periodic=False, debug="interval")

    def uplink(self):
        if self.counter < self.REDUNDANCY_CONST:
            self.channel.send(copy.deepcopy(self.default_data))

            scheduler = self.uplink_arg[0]
            scheduler.uplink(self.uplink_arg)

    def set_alarm(self, callback, interval, periodic=False, debug=None):
        def alarm():
            time_0 = time.time()

            while (time.time() - time_0) < interval:
                if self.cancel_flag.isSet():
                    return

                time.sleep(0.01)

            callback()

        alarm_thread = _thread.start_new_thread(alarm, tuple())

        return alarm_thread

