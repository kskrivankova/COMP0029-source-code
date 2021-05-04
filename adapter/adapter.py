from .ring_buffer import RingBuffer, RingBufferUnderflow
from copy import deepcopy

import _thread
import datetime
import os


class Node:
    def __init__(self):
        self.node_thread = None

    def start(self, run_callback, *args):
        return _thread.start_new_thread(run_callback, args)


class Void:
    latest_id = 0
    void = []
    lock = _thread.allocate_lock()
    links = None

    def __init__(self, links):
        self.links = links

    def init_node(self):
        new_id = self.latest_id
        self.void.append(RingBuffer(10))

        self.latest_id += 1

        return new_id

    def send(self, data, node_id):
        self.lock.acquire()
        node_links = {}

        if self.links:
            node_links = self.links[node_id]

        for i, buffer in enumerate(self.void):
            if i == node_id:
                continue
            elif node_links and (i not in node_links):
                continue

            buffer.push(deepcopy(data))

        self.lock.release()

    def recv(self, node_id):
        self.lock.acquire()
        data = None

        try:
            data = self.void[node_id].pop()
        except RingBufferUnderflow:
            pass
        finally:
            self.lock.release()

        return data


class LoRa:
    LORA = "LoRa"
    EU868 = "EU868"

    def __init__(self, mode=None, region=None):
        self.mode = mode
        self.region = region


class socket:
    test = "test"
    blocking = True
    AF_LORA = "af_LoRa"
    SOCK_RAW = "sock_raw"
    links = {}
    void = Void(links)

    def __init__(self, address_family, socket_type):
        self.address_family = address_family
        self.socket_type = socket_type
        self.node_id = self.void.init_node()

    def setblocking(self, flag):
        self.blocking = flag

    def send(self, data):
        self.void.send(data, self.node_id)

    def recv(self, buffer_size):
        return self.void.recv(self.node_id)


class RTC:
    def init(self, datetime=None):
        self.datetime = datetime if datetime else None
        self.year, self.month, self.day, self.hour, self.minute, self.sec, self.usec, self.tzone = datetime if datetime else None

    def now(self):
        now = datetime.datetime.now()
        timestamp = datetime.datetime.timestamp(now)
        return now


def getrandbits(bits):
    num_bytes = bits // 8
    return os.urandom(num_bytes)
