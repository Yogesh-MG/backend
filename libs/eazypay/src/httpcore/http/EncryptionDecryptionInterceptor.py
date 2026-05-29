
import json, os
from ..AppConstants import AppConstants
from ..dto.EncryptedPayloadDTO import EncryptedPayloadDTO
from ..dto.EncryptedResponseDTO import EncryptedResponseDTO
from ..http.SdkHttpException import SDKClientException
from ..utils.CryptoUtility import CryptoUtility
from ..utils.decryptionUtiility import decrypt
from ..utils.log import logger
from base64 import b64encode



class EncryptionDecryptionInterceptor():
    crypto_utility: CryptoUtility = CryptoUtility()

    def encrypt_request(self, plain_text_body: str, pem_path_for_module: str) -> str:
        """
        Encrypts the plain text request payload.
        """
        try:
            encrypted_request_body = self._get_encrypted_payload_dto(plain_text_body, pem_path_for_module)
            logger.debug(f"Request payload encrypted successfully. encryptedPayload={encrypted_request_body.model_dump_json()}")
            return encrypted_request_body
        except Exception as e:
            logger.error("Failed to encrypt the request payload", exc_info=True)
            raise ValueError("Encryption failed") from e

    def decrypt_response(self, encrypted_response_body: str) -> str:
        """
        Decrypts the encrypted response payload.
        """
        logger.debug(f"encryptedResponseBody = {encrypted_response_body}")
        try:
            try:
                encrypted_response_body_dto = EncryptedResponseDTO(**encrypted_response_body)
            except json.JSONDecodeError as e:
                logger.error("Unable to parse as the response from the server is not in encrypted JSON", exc_info=True)
                raise SDKClientException("Business Error occurred") from e

            decrypted_body = decrypt(encrypted_response_body_dto.encryptedKey, 
                                 encrypted_response_body_dto.encryptedData)

            logger.debug(f"decryptedBody = {decrypted_body}")
            return decrypted_body
        except SDKClientException as e:
            logger.error(f"errorMessage = {e}")
            raise ValueError(f"Decryption failed, errorMessage = {e}") from e
        except Exception as e:
            logger.error("Failed to decrypt the response payload", exc_info=True)
            raise ValueError("Decryption failed") from e

    def _get_encrypted_payload_dto(self, plain_text_request_body: str, pem_path: str) -> EncryptedPayloadDTO:
        """
        Generates an encrypted payload DTO from plain text.
        """
        random_key = self.crypto_utility.generate_random_key(AppConstants.KEY_LENGTH)
        server_public_key = self.crypto_utility.load_public_key(pem_path)
        logger.debug(f"Random key for encrypting payload, randomKey = {random_key}")

        base64_message_key =  random_key.encode().decode()
        iv_key = self.crypto_utility.generate_random_key(AppConstants.IV_KEY_LENGTH)

        """ Cryptography """
        encrypted_random_key = self.crypto_utility.encrypt_key(base64_message_key, server_public_key)
        encrypted_payload_data = self.crypto_utility.encrypt_data(random_key, iv_key, plain_text_request_body)

        return self._construct_encrypted_payload_dto(encrypted_payload_data, encrypted_random_key)

    def _construct_encrypted_payload_dto(self, encrypted_payload_data: str,
                                         encrypted_random_key: str) -> EncryptedPayloadDTO:
        """
        Constructs the EncryptedPayloadDTO object.
        """
        return EncryptedPayloadDTO(
            encryptedData = encrypted_payload_data,
            encryptedKey= encrypted_random_key,
            service="proxyPathSuffix",  # TODO: Update based on production value
            oaepHashingAlgorithm= "NONE",  # TODO: Update based on production value
            requestId="",
            iv="",
            clientInfo="",
            optionalParam=""
        )


