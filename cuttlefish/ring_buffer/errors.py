class RingBufferOverflow(Exception):
    """
    Raised when scheduler buffer size is exceeded
    """

    pass


class RingBufferUnderflow(Exception):
    """
    Raised when user tries to pop an item from an empty buffer
    """

    pass


class BufferSizeNotAllowed(Exception):
    """
    Raised when max_size specified is smaller than 1
    """

    pass
