
import requests, json
from ..AppConstants import AppConstants
from .EncryptionDecryptionInterceptor import EncryptionDecryptionInterceptor
from ..utils.CryptoUtility import CryptoUtility
from ..utils.log import logger


# Constants for timeout durations (in seconds)
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
WRITE_TIMEOUT = 30

interceptor = EncryptionDecryptionInterceptor()


class CoreHttpClient():
    """
        Core HTTP Client for sending HTTP POST requests with headers and payload.
        """
    public_key_path  = None
    apiKey = None

    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def get_settings(self, name, category):
        if name == 'corporate' or (name == 'composite' and category == "cib"):
            self.public_key_path = AppConstants.CIB_PUBLIC_KEY_PATH
            self.apiKey = AppConstants.CIB_API_KEY
        elif name == 'composite':
            self.public_key_path = AppConstants.COMPOSITE_PUBLIC_KEY_PATH
            self.apiKey = AppConstants.COMPOSITE_API_KEY
        elif name == 'eazypay':
            self.public_key_path = AppConstants.EAZYPAY_PUBLIC_KEY_PATH
            self.apiKey = AppConstants.EAZYPAY_API_KEY
        elif name == 'cibbulk':
            self.public_key_path = AppConstants.CIBBULK_PUBLIC_KEY_PATH
            self.apiKey = AppConstants.CIBBULK_API_KEY     
        logger.info(f"API KEY : {self.apiKey}")

    @classmethod
    def prepare_headers(self, body, kwargs):

        crypto_utility = CryptoUtility()
        finger_print = crypto_utility.generate_xid_fingerprint_header(body,
                                    self.apiKey, self.public_key_path)
        headers = { 
                    "Content-Type": AppConstants.APPLICATION_JSON_CHARSET_UTF_8,
                    "X-SDK-Originated" : "true",
                    "X-SDK-VERSION":"1.0",
                    AppConstants.API_KEY : self.apiKey,
                    AppConstants.X_ID_FINGERPRINT : finger_print,
                }
        if kwargs.get('priority'):
            headers[AppConstants.X_PRIORITY_HEADER] = kwargs.get('priority')

        return headers


    @classmethod
    def common_api_call(self, endpoint, body, kwargs):
        """
        Makes an HTTP request using the provided client certificate.

        Args:
            url: The URL to make the request to.
            cert_file: Path to the client certificate file (e.g., 'client.crt').
            key_file: Path to the client key file (e.g., 'client.key').

        Returns:
            The response object from the request.
        """
        try:
            self.get_settings(kwargs.get('name'), kwargs.get('category'))
            if not isinstance(body, dict):
                body_in_string = body.model_dump_json(by_alias= True ,exclude_none=True)
            else:
                body_in_string = json.dumps(body) if isinstance(body,dict) else body
                
            print("Request Body", body_in_string)
            logger.info(f"Request Body: {body_in_string}")
            headers = self.prepare_headers(body_in_string, kwargs)
            body = interceptor.encrypt_request(body_in_string, self.public_key_path)
            body = body.model_dump(by_alias= True)
            url = AppConstants.BASE_URL + endpoint
            response = None
            json_response = None
            print("Url",url)
            logger.info(f"Url: {url}")
            logger.info(f"Encrypted Request: {body}")
            print("Encrypted Request",body)


            try:
                response = requests.post(
                url,
                json=body,
                headers=headers,
                verify=True,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )

                try:
                    json_response = response.json()
                    enckey = json_response.get("encryptedKey")
                    encData = json_response.get("encryptedData")
                    print("Encrypted Response", json_response)
                    logger.info(f"Encrypted Response: {json_response}")
                    if encData and enckey:
                        json_response = interceptor.decrypt_response(json_response)
                    logger.info(f"Decrypted Response: {json_response}")
                    return json_response

                except ValueError:
        # If response is not JSON, return raw text
                    print("Response is not JSON. Raw response:")
                    print(response.text)
                    return response.text

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return # TODO
