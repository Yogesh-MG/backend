from pydantic import BaseModel
from SdkHttpException import (
    SdkHttpException,
    ValidationException,
    AuthenticationException,
    AccessDeniedException,
    ResourceNotFoundException,
    ServerErrorException,
)
from ..utils.log import logger

class ResponseHandler(BaseModel):
    @staticmethod
    def handle_response(response):
        """
        Handles the HTTP response based on its status code.

        :param response: The HTTP response object.
        :return: The response body if the status code indicates success.
        :raises SdkHttpException: if the response status code indicates an error.
        """
        status_code = response.status_code
        response_body = ""

        try:
            response_body = response.text if response.text else ""
            logger.debug(f"Response Body: {response_body}")
        except Exception as e:
            logger.error("Error reading the response body", exc_info=True)
            raise SdkHttpException.SdkHttpException("Error reading the response body") from e

        if status_code in [200, 201]:
            logger.info(f"Successful response with status code: {status_code}")
            return response_body

        elif status_code == 400:
            logger.warning(f"Bad Request: {response_body}")
            raise ValidationException("Bad Request", response_body)

        elif status_code == 401:
            logger.warning(f"Unauthorized access - {response_body}")
            raise AuthenticationException("Unauthorized access", response_body)

        elif status_code == 403:
            logger.warning(f"Forbidden access - {response_body}")
            raise AccessDeniedException("Forbidden access", response_body)

        elif status_code == 404:
            logger.warning(f"Resource not found - {response_body}")
            raise ResourceNotFoundException("Not Found", response_body)

        elif status_code == 500:
            logger.error(f"Internal Server Error - {response_body}")
            raise ServerErrorException("Internal Server Error", response_body)

        elif status_code == 502:
            logger.error(f"Bad Gateway - {response_body}")
            raise ServerErrorException("Bad Gateway", response_body)

        elif status_code == 503:
            logger.error(f"Service Unavailable - {response_body}")
            raise ServerErrorException("Service Unavailable", response_body)

        elif status_code == 504:
            logger.error(f"Gateway Timeout - {response_body}")
            raise ServerErrorException("Gateway Timeout", response_body)

        else:
            logger.error(f"Unexpected Response Code: {status_code} - {response_body}")
            raise SdkHttpException(f"Unexpected Response Code: {status_code}", response_body)
