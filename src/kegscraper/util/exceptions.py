"""Exceptions for the kegscraping package"""

class UnclosedJSONError(Exception):
    """
    Raised when a JSON string is never closed.
    """
    pass

class NotFound(Exception):
    pass

class ParseFailure(Warning):
    pass

class Unauthorised(Exception):
    pass

class ServerError(Exception):
    pass

class TimeOut(Exception):
    pass

class UnimplementedWarning(Warning):
    pass

class WebServiceError(Exception):
    pass