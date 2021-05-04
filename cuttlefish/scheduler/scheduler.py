from .errors import *
from .modes import *

try:
    from adapter.sim_modes import implicitly_synchronous_schedule_sim
except:
    implicitly_synchronous_schedule_sim = None


ASYNCHRONOUS_SIMPLE = asynchronous_schedule
IMPLICIT_SYNCHRONOUS = implicitly_synchronous_schedule_sim if implicitly_synchronous_schedule_sim else implicitly_synchronous_schedule
IMPLICIT_SYNCHRONOUS_GATEWAY = implicitly_synchronous_schedule_gateway
SYNCHRONOUS = synchronous_schedule
FLOODING = None


class Scheduler:
    """
    Scheduler manages sending and receiving of packets within bounds of a logical channel. There is exactly one
    Scheduler object instantiated during runtime.
    Scheduler needs reference to a orchestrator object and either a mode or schedule_callback when initialized. It is
    possible to redefine uplink and downlink functions by setting uplink_callback and downlink_callback respectively.

    Scheduler receives packets to be sent from the Director thread in a buffer. Received packets are pushed to the
    Director for further processing.

    Modes
    User can choose one of the implemented modes to determine pattern in which packets will be sent (uplink) and
    received (downlink).

    mode =  "synchronous" |
            "implicitly_synchronous" |
            "slotted"

    Synchronous

    Implicitly synchronous

    Slotted

    """

    def __init__(self, orchestrator):
        # TODO: optimal default buffer size
        self.orchestrator = orchestrator
        self.channels = {}

        self.uplink = None
        self.downlink = None

        self.socket = None

    def set_connection_parameters(
        self,
        socket,
        channel_id,
        *args,
        mode=None,
        uplink_callback=None,
        downlink_callback=None,
        schedule_callback=None,
        **kwargs
    ):

        if (not mode) and (not schedule_callback):
            raise UndefinedSchedulerBehaviour

        self.socket = socket

        mode = schedule_callback if schedule_callback else mode
        mode_args = [self, channel_id]
        mode_args.extend(args)
        mode_kwargs = kwargs

        self.channels.update({channel_id: {
                                            "mode": mode,
                                            "mode_args": mode_args,
                                            "mode_kwargs": mode_kwargs
                                            }
                              })

        self.uplink = uplink_callback if uplink_callback else uplink
        self.downlink = downlink_callback if downlink_callback else downlink

        if (mode == IMPLICIT_SYNCHRONOUS) or (mode == IMPLICIT_SYNCHRONOUS_GATEWAY) or (mode == SYNCHRONOUS):
            return mode(*mode_args, **mode_kwargs)

        return

    def start(self):
        if not self.socket:
            raise UndefinedConnectionParameters(
                "Connection not initialized by channel"
            )

        if not self.channels:
            raise UndefinedChannel(
                "Connection not initialized by channel"
            )

        for channel in self.channels.values():
            callback = resolve_callback(channel.get("mode"))

            if callback != ASYNCHRONOUS_SIMPLE:
                continue

            mode_args = channel.get("mode_args")
            mode_kwargs = channel.get("mode_kwargs")

            channel["cancel_flag"] = callback(*mode_args, **mode_kwargs)

    def get_packet(self, channel_id):
        return self.orchestrator.get_packet(channel_id)

    def submit_received_bytes(self, channel_id, packet_bytes, meta):
        self.orchestrator.add_task(channel_id, 1, (packet_bytes, meta))


def uplink(args):
    scheduler = args[0]
    channel_id = args[1]
    kwargs = args[2]

    sent_callback = kwargs.get("sent_callback")
    sent_args = tuple() if not kwargs.get("sent_args") else kwargs.get("sent_args")

    data = scheduler.get_packet(channel_id)
    socket = scheduler.socket

    if data:
        socket.setblocking(True)
        socket.send(data)
        socket.setblocking(False)

        if sent_callback:
            sent_callback(data, *sent_args)

        return True

    return False


def downlink(args):
    scheduler = args[0]
    kwargs = args[1]
    # TODO: Fix this
    channel_id = kwargs

    buffer_size = kwargs.get("buffer_size") if kwargs.get("buffer_size") else 32
    recv_callback = kwargs.get("recv_callback")
    recv_args = tuple() if not kwargs.get("recv_args") else kwargs.get("recv_args")

    data = b""
    meta = {}
    new_data = True

    socket = scheduler.socket
    socket.setblocking(False)

    while new_data:
        new_data = socket.recv(buffer_size)
        meta.update({"time_recv": scheduler.orchestrator.rtc.now()})

        if new_data:
            data += new_data

    if data:
        received_channel_id = data[0]
        scheduler.submit_received_bytes(received_channel_id, data[1:], meta)

        if recv_callback:
            recv_callback(data, *recv_args)

        if received_channel_id == channel_id:
            return True

        return False

    return False


def resolve_callback(mode):
    if callable(mode):
        return mode

    raise UndefinedMode("Scheduler: mode defined by user does not exist")
