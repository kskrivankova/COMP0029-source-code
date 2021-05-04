class AttributeSizeNotAllowed(Exception):
    """
    Raised when attribute size is smaller than 0
    """

    pass


class AttributeTypeNotRecognized(Exception):
    """
    Raised when an attribute type defined in scheme is not recognized
    """

    pass


class CallbackNotDefined(Exception):
    """
    Raised when a callback was not defined in a scheme describing an attribute of variable size
    """

    pass


class UnexpectedInputSize(Exception):
    """
    Issued when the expected size defined by a scheme does not match input size received
    """

    pass


class RedundantBytesReceived(Exception):
    """
    Issued when the expected the received input is longer than expected
    """

    pass
