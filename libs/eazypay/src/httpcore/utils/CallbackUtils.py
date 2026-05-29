from httpcore.http.EncryptionDecryptionInterceptor import EncryptionDecryptionInterceptor
from httpcore.utils.log import logger

interceptor = EncryptionDecryptionInterceptor()

def decrypt_callback(encrypted_response: dict):
    """
    Decrypts the response containing 'encryptedData' and 'encryptedKey'.

    Args:
        encrypted_response (dict): The encrypted response received from an API.

    Returns:
        dict | None: Decrypted response if successful, else None.
    """
    try:
        encrypted_key = encrypted_response.get("encryptedKey")
        encrypted_data = encrypted_response.get("encryptedData")
        
        if encrypted_key and encrypted_data:
            decrypted_response = interceptor.decrypt_response(encrypted_response)
            return decrypted_response
        else:
            logger.warning("Missing encryptedKey or encryptedData in the response.")
            return None
    except Exception as e:
        logger.error(f"Error while decrypting response: {str(e)}")
        return None
