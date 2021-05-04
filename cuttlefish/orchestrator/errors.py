class UnknownTaskTypeError(Exception):
    """
    Raised if orchestrator encounters a ward of unknown type
    """

    pass


class UndefinedChannel(Exception):
    """
    Raised if orchestrator does not have reference to the requisite logical channel
    """

    pass


class ChannelDoesNotExist(Exception):
    """
    Raised if orchestrator tries to process task through a channel not in channels dict
    """

    pass


class TaskBufferFull(Exception):
    """
    Issued when orchestrator buffer overflows
    """

    pass
