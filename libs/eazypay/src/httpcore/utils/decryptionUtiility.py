from cryptography.hazmat.primitives.serialization import pkcs12,  pkcs7
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from httpcore.utils.CryptoUtility import CryptoUtility
from httpcore.AppConstants import AppConstants
from httpcore.utils.log import logger
import os



def load_private_key(key_file_path, keystore_password=None):
    """
    Loads the private key from a .p12 or .pem file.

    Args:
        key_file_path: Path to the file containing the private key.
        keystore_password: Password to decrypt the private key if it's encrypted.

    Returns:
        The loaded private key object, or None if an error occurs.
    """
    try:
        file_ext = os.path.splitext(key_file_path)[1].lower()

        with open(key_file_path, "rb") as key_file:
            key_bytes = key_file.read()

            if file_ext in [".p12", ".pfx"]:
                private_key, certificate, othercerts = pkcs12.load_key_and_certificates(
                    key_bytes,
                    password=keystore_password.encode() if keystore_password else None,
                    backend=default_backend()
                )
                return private_key

            elif file_ext == ".pem":
                # Try loading without a password first
                try:
                    private_key = serialization.load_pem_private_key(
                        key_bytes,
                        password=None,
                        backend=default_backend()
                    )
                    return private_key
                except TypeError as e:
                    if "private key is encrypted" in str(e):
                        # Retry with password if encryption is detected
                        if not keystore_password:
                            logger.error("Private key is encrypted but no password was provided.")
                            return None
                        private_key = serialization.load_pem_private_key(
                            key_bytes,
                            password=keystore_password.encode(),
                            backend=default_backend()
                        )
                        return private_key
                    else:
                        raise

            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return None

    except Exception as e:
        logger.error(f"Failed to load private key from {key_file_path}: {e}")
        return None


def decrypt(encrypted_key, encrypted_data):
    try:
        keystore_path = AppConstants.EAZYPAY_KEYSTORE_PATH
        keystore_password = AppConstants.EAZYPAY_KEYSTORE_PASSWORD

        if not keystore_path or not keystore_path.strip():
            logger.error("Keystore path is not provided.")
            raise Exception("Keystore path is not provided.")

        if not keystore_password or not keystore_password.strip():
            logger.error("Keystore password is not provided.")
            return None

        private_key = load_private_key(keystore_path, keystore_password)

        if not private_key:
            logger.error("Failed to load private key from keystore.")
            return None

        crypto_utility = CryptoUtility()
        decrypted_key = crypto_utility.decrypt_key(encrypted_key, private_key)

        if not decrypted_key:
            logger.error("Failed to decrypt the encrypted key using RSA.")
            return None

        logger.debug("decryptedKey: %s", decrypted_key)
        decrypted_data = crypto_utility.decrypt_data(encrypted_data, decrypted_key)

        if not decrypted_data:
            logger.error("Failed to decrypt the encrypted data using AES.")
            return None

        return decrypted_data

    except Exception as e:
        raise ValueError(f"Unexpected error during decryption: {e}")
        
