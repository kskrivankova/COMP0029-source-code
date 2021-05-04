class NoAckMatched(Exception):
    """
    Raised if ack received does not match any packet awaiting an ack for this node
    """

    pass
