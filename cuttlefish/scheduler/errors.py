class UndefinedConnectionParameters(Exception):
    """
    Raised when connection is not initialized by logical channel
    """

    pass


class UndefinedMode(Exception):
    """
    Raised when scheduler encounters a mode that has not been defined
    """

    pass


class UndefinedChannel(Exception):
    """
    Raised when no channels have been supplied to scheduler
    """

    pass


class UndefinedSchedulerBehaviour(Exception):
    """
    Raised when neither mode nor schedule_callback is defined for scheduler
    """

    pass


class PacketsToBeScheduledDropped(Exception):
    """
    Issued when scheduler packet buffer is full
    """
