from .errors import *
from cuttlefish.packet_management import attr, INT
from cuttlefish.ring_buffer import RingBuffer

from _thread import allocate_lock

try:
    import os
except ModuleNotFoundError:
    pass

NEEDS_ACK = 1
IS_ACK = 2


class Network:
    def __init__(self, address, *args, address_size=4, counter_size=3, meta=None, buffer_size=10, **kwargs):
        self.meta = meta
        self.address = address
        self.address_size = address_size
        self.promiscuous_address = bytes(address_size)

        self.address_scheme = attr("address", address_size, type="b")
        self.id_address_scheme = attr("sender_address", address_size, type="b")
        self.counter_scheme = attr("counter", counter_size, type=INT)

        self.orchestrator = None
        self.scheduler = None
        self.channel_id = None

        self.immediate_send = None
        self.immediate_recv = None

        self.counter = False
        self.identified = False
        self.ack = False

        self.counter_send_index = None
        self.counter_recv_index = None

        self.packet_id = None
        self.ack_request_index = None

        self.ack_await_index = None
        self.send_ack = RingBuffer(buffer_size)
        self.next_ack_id = None
        self.ack_callback = None

    def init_connection(
        self,
        socket,
        channel_id,
        serializer,
        orchestrator,
        scheduler,
        *args,
        identified=False,
        ack=False,
        ack_callback=None,
        counter=False,
        channel=None,
        mode=None,
        schedule_callback=None,
        recv_buffer_size=None,
        **kwargs
    ):
        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self.channel_id = channel_id

        self.counter = counter
        self.identified = identified
        self.ack = ack

        if counter:
            self.identified = True
            serializer.add_layer(headers=[self.counter_scheme])
            self.counter_send_index = {0: 0}
            self.counter_recv_index = {0: 0}

        if ack:
            self.identified = True

            self.ack_await_index = {}
            self.ack_callback = ack_callback

            ack_type_scheme = attr("ack_type", 1, type=INT)
            packet_id_scheme = attr("packet_id", 1, type=INT)
            id_await_scheme = attr("ack_await_id", 1, type=INT)

            serializer.add_layer(headers=[packet_id_scheme, ack_type_scheme, id_await_scheme])

            # Generate starting id value
            self.packet_id = int.from_bytes(os.urandom(1), "big")

        if ack | counter | identified:
            serializer.add_layer(headers=[self.id_address_scheme])

        immediate_transmit = self.scheduler.set_connection_parameters(
            socket,
            channel_id,
            *args,
            mode=mode,
            schedule_callback=schedule_callback,
            recv_buffer_size=recv_buffer_size,
            **kwargs
        )

        (self.immediate_send, self.immediate_recv) = immediate_transmit if immediate_transmit else (None, None)

    def process_send(self, data, meta, *args, ack_type=0, ack_req_id=None, packet_id=None, **kwargs):
        # TODO: construct a pipeline as in measures
        if self.counter:
            self.counter_send(data, *args)

        if self.ack:
            self.ack_send(data, meta, ack_type, ack_req_id=ack_req_id, packet_id=packet_id)

        if self.identified:
            self.identified_send(data)

    def process_recv(self, data, meta, *args, **kwargs):
        if self.identified:
            self.identified_recv(data, meta)

        if self.ack:
            self.ack_recv(data, meta)

        if self.counter:
            data = self.counter_recv(data, meta)

        return data

    def send(self, data, *args, **kwargs):
        self.orchestrator.send_packet(self.channel_id, data)

        if self.immediate_send:
            self.immediate_send()

    def receive(self):
        if self.immediate_recv:
            self.immediate_recv()

        return self.orchestrator.retrieve(self.channel_id)

    def disconnect(self):
        self.orchestrator.running[self.channel_id] = False
        self.orchestrator.send[self.channel_id].clear()
        self.orchestrator.processed[self.channel_id].clear()

    def find_remove(self, ack_id):
        """
        Find packet waiting for an ack - if found, remove it from dictionary. If no ack is matched, return.
        """
        id_entry = self.ack_await_index.get(ack_id)

        if not id_entry:
            return False

        if self.ack_callback:
            self.ack_callback(ack_id)

        del id_entry

        return True

    def new_id(self):
        self.packet_id = (self.packet_id + 1) % 256
        return self.packet_id

    def counter_send(self, data, *args):
        dest_address = args[0] if args else None

        if args:
            dest_address = args[0]
        else:
            self.counter_send_index[0] = self.counter_send_index[0] + 1

        if self.counter_send_index.get(dest_address):
            counter = self.counter_send_index[dest_address]
            self.counter_send_index[dest_address] = counter + 1
        else:
            counter = 0
            self.counter_send_index[dest_address] = 1

        data.append([counter])

        return data

    def counter_recv(self, data, meta):
        recv_counter = data.pop()
        recv_counter = recv_counter["counter"]

        sender_address = meta["sender_address"]
        counter = self.counter_recv_index[sender_address] if self.counter_recv_index.get(sender_address) else recv_counter

        if recv_counter < counter:
            return None
        if recv_counter >= counter:
            self.counter_recv_index[sender_address] = recv_counter + 1

        return data

    def identified_send(self, data):
        data.append([self.address])

    def identified_recv(self, data, meta):
        id_layer = data.pop()
        sender_address = id_layer["sender_address"]

        meta.update({"sender_address": sender_address})

    def ack_send(self, data, meta, ack_type, ack_req_id=None, packet_id=None):
        """
        Packet acknowledgment types:
            00... no acknowledgment required
            01... needs acknowledgment
            10... is an acknowledgment
            11... needs an acknowledgment and is an acknowledgment
        """
        if not packet_id:
            packet_id = self.new_id()

        meta.update({"packet_id": packet_id})
        # print("Meta: {}".format(id(meta)))

        ack_layer = [packet_id, ack_type]

        # Check whether 'is acknowledgment' bit is set
        if ack_type & IS_ACK:
            if ack_req_id:
                ack_id = ack_req_id
            else:
                ack_id = self.next_ack_id

            if ack_id:
                ack_layer.append(ack_id)
            else:
                ack_layer.append(0)
        else:
            ack_layer.append(0)

        if ack_type & NEEDS_ACK:
            self.ack_await_index.update({packet_id: ack_type})

        data.append(ack_layer)

    def ack_recv(self, data, meta):
        ack_layer = data.pop()

        ack_type = ack_layer.get("ack_type")
        packet_id = ack_layer.get("packet_id")
        ack_id = ack_layer.get("ack_await_id")

        meta.update({"ack_type": ack_type})

        if not ack_type:
            return

        if ack_type & NEEDS_ACK:
            meta.update({"packet_id": packet_id})

        if ack_type & IS_ACK:
            success = self.find_remove(ack_id)

            if success:
                meta.update({"ack_req_id": ack_id})
            else:
                pass
                # raise NoAckMatched("No ack matching ack id {} found in ack index".format(ack_id))
