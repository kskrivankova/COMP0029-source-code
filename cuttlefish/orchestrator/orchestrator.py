from cuttlefish.ring_buffer import *
from .errors import *

import _thread

try:
    from machine import RTC
except ModuleNotFoundError:
    from adapter import RTC


SEND = 0
RECEIVED = 1
PROCESSED = 2


class Orchestrator:
    def __init__(
        self,
        max_process_buffer_size=10,
        max_buffer_size=10,
    ):
        self.rtc = RTC()
        self.rtc.init((0, 0, 0, 0, 0, 0, 0, 0))

        self.tasks = RingBuffer(max_process_buffer_size)
        self.processed = None
        self.send = None
        self.max_buffer_size = max_buffer_size

        self.task_lock = _thread.allocate_lock()
        self.processed_lock = _thread.allocate_lock()
        self.send_lock = _thread.allocate_lock()

        self.director_thread = None
        self.channels = None
        self.running = None

        self.processed_callback = {}

    def start(self):
        self.director_thread = _thread.start_new_thread(self.orchestrate, ())

    def add_channels(self, *args):
        self.channels = dict([(channel.get_id(), channel) for channel in args])
        self.running = dict([(channel.get_id(), True) for channel in args])
        self.processed = dict([(channel.get_id(), RingBuffer(self.max_buffer_size)) for channel in args])
        self.send = dict([(channel.get_id(), RingBuffer(self.max_buffer_size)) for channel in args])

    def send_packet(self, channel_id, packet_bytes):
        try:
            self.send_lock.acquire()

            packet_id = channel_id.to_bytes(1, "big")
            packet_bytes = packet_id + packet_bytes

            self.send[channel_id].push(packet_bytes)

            return 1

        except RingBufferOverflow:
            return 0
        except KeyError:
            raise (ChannelDoesNotExist, "Orchestrator tried to retrieve packets from a buffer for a channel not in "
                                        "channel dictionary. Use add_channels method to register channels.")
        finally:
            self.send_lock.release()

    def get_packet(self, channel_id):
        packet = None
        try:
            self.send_lock.acquire()

            packet = self.send[channel_id].pop()
        except RingBufferUnderflow:
            pass
        finally:
            self.send_lock.release()

        return packet

    def add_task(self, channel_id, task_type, assignment):
        try:
            self.task_lock.acquire()

            task = (channel_id, task_type, assignment)
            self.tasks.push(task)
        finally:
            self.task_lock.release()

    def retrieve(self, channel_id):
        try:
            self.processed_lock.acquire()

            processed_data = self.processed[channel_id].pop()

            return processed_data

        except RingBufferUnderflow:
            return None, {}
        except KeyError:
            raise(ChannelDoesNotExist, "Orchestrator tried to retrieve packets from a buffer for a channel not in "
                                       "channel dictionary. Use add_channels method to register channels.")
        finally:
            self.processed_lock.release()

    def orchestrate(self):
        """
        Process tasks submitted to orchestrator buffer.
        type: tuple [0]: channel id
                    [1]: assignment
                    [2]: content

        Assignment types:
            0... to be sent
            1... received
            2... processed
        """
        while True:
            if not self.channels:
                raise UndefinedChannel("Orchestrator: no channel defined")

            self.task_lock.acquire()

            try:
                task = self.tasks.pop()

                self.process_task(task[0], task[1], task[2])

            except RingBufferUnderflow:
                pass
            except RingBufferOverflow:
                # Drop tasks if buffer is overflowing
                pass
            except KeyError:
                raise ChannelDoesNotExist(
                    "Orchestrator tried to access channel that has not been added."
                )
            finally:
                self.task_lock.release()

    def process_task(self, channel_id, assignment, content):
        if not self.running[channel_id]:
            return

        if assignment == RECEIVED:
            data, meta = content
            decoded = self.channels[channel_id].process(data, meta)
            meta.update({"time_processed": self.rtc.now()})

            if decoded:
                task = (channel_id, 2, (decoded, meta))
                self.tasks.push(task)

        elif assignment == PROCESSED:
            # TODO: not use processed buffer if processed_callback is defined?
            self.processed[channel_id].push(content)

            if self.processed_callback.get(channel_id):
                self.processed_callback.get(channel_id)(content)
        else:
            raise UnknownTaskTypeError
