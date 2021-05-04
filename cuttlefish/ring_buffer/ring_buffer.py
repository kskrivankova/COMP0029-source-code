from .errors import *

import _thread


class RingBuffer:
    def __init__(self, max_size):
        if max_size < 1:
            raise BufferSizeNotAllowed

        self.max_size = max_size
        self.current_size = 0

        self.buffer = [None] * max_size
        self.head = 0
        self.tail = -1

        self.lock = _thread.allocate_lock()

    def __repr__(self):
        return str(self.buffer)

    def push(self, *args):
        with self.lock:
            if (self.current_size + len(args)) > self.max_size:
                raise RingBufferOverflow

            for arg in args:
                self.tail = (self.tail + 1) % self.max_size
                self.buffer[self.tail] = arg

                self.current_size += 1

    def pop(self):
        with self.lock:
            if self.current_size == 0:
                raise RingBufferUnderflow

            result = self.buffer[self.head]
            self.buffer[self.head] = None
            self.head = (self.head + 1) % self.max_size

            self.current_size -= 1

            return result

    def clear(self):
        self.buffer = [None] * self.max_size
