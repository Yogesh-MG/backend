
class SDKClientException(Exception):
    """
    Args:
        message (str): The error message for the exception.
    """

    def __init__(self, message: str):
        super().__init__(message)


class SdkHttpException(Exception):
    def __init__(self, message: str, response_body: str = None, cause: Exception = None):
        super().__init__(message)
        self.response_body = response_body
        self.__cause__ = cause

class AuthenticationException(SdkHttpException):
    def __init__(self, message: str, response_body: str):
        super().__init__(message, response_body)


class ResourceNotFoundException(SdkHttpException):
    def __init__(self, message: str, response_body: str):
        super().__init__(message, response_body)


class AccessDeniedException(SdkHttpException):
    def __init__(self, message: str, response_body: str):
        super().__init__(message, response_body)


class ServerErrorException(SdkHttpException):
    def __init__(self, message: str, response_body: str):
        super().__init__(message, response_body)


class ValidationException(SdkHttpException):
    def __init__(self, message: str, response_body: str):
        super().__init__(message, response_body)
