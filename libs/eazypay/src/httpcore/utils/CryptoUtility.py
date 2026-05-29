from __future__ import annotations
import os
import base64
import binascii
import random
import hashlib
from typing import Optional
from base64 import b64encode, b64decode

from httpcore.utils.FileLoaderUtil import FileLoaderUtil
from httpcore.utils.SingletonManager import Singleton
from httpcore.utils.log import logger
from httpcore.AppConstants import AppConstants
from httpcore.http.SdkHttpException import SDKClientException


# cryptography
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend



class CryptoUtility(Singleton):

    def pkcs5_padding(self, message, block_size):
        """Pads a message according to PKCS#5 padding scheme.

        Args:
            message: The message to be padded (bytes).
            block_size: The size of the block (int).

        Returns:
            The padded message (bytes).
        """

        padding_length = block_size - (len(message) % block_size)
        padding = bytes([padding_length] * padding_length)
        return message + padding

    def pkcs5_unpadding(self, padded_message):
        """Removes PKCS#5 padding from a message.

        Args:
            padded_message: The padded message (bytes).

        Returns:
            The original message (bytes).
            Raises ValueError if padding is invalid.
        """
        if not padded_message:
            raise ValueError("Empty padded message")

        padding_length = padded_message[-1]  # Get padding length from the last byte

        if padding_length > len(padded_message) or padding_length == 0:
            raise ValueError("Invalid padding length")

        padding = padded_message[-padding_length:]

        if padding != bytes([padding_length] * padding_length): #Check if the padding bytes are correct.
            raise ValueError("Invalid padding bytes")


        return padded_message[:-padding_length]

    def rsa_encrypt(self, message: str, public_key):
        ciphertext = public_key.encrypt(
            message.encode(),
            padding.PKCS1v15()  # Use PKCS1v15 padding in the encrypt function as well
        )
        return ciphertext

    def rsa_decrypt(self, ciphertext, private_key):
        padded_message = private_key.decrypt(
            ciphertext,
            padding.PKCS1v15() # Use PKCS1v15 padding in the decrypt function as well
        )
        return padded_message

    def load_public_key(self, filename: str):
        """
        Loads an RSA public key from a file.

        :param filename: The path to the public key file.
        :return: An RSA public key object.
        :raises Exception: If the key cannot be loaded or parsed.
        """
        try:
            pem_encoded_public_key_bytes = FileLoaderUtil.load_file_as_stream(filename)
            key = serialization.load_pem_public_key(pem_encoded_public_key_bytes)
            return key
        except Exception as e:
            raise ValueError(f"Invalid PEM-encoded public key: {e}")


    def load_private_key(self, filename: str, password = None):
        try:
            key_bytes = FileLoaderUtil.load_file_as_stream(filename)
            # Convert bytes to string and remove PEM header/footer
            private_key = serialization.load_pem_private_key(
                            key_bytes, 
                            password= password.encode() if password else None, 
                            backend=default_backend()
                        )
            return private_key

        except Exception as e:
            raise Exception(f"Error loading private key: {e}")

    def encrypt_key(self, message: str, public_key) -> str:
        try:
            ciphertext = self.rsa_encrypt(message, public_key)
            return b64encode(ciphertext).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error encrypting message: {e}")

    def encrypt_data(self, key: str, init_vector: str, message: str) -> Optional[str]:
        try:
            # Encryption    
            cipher = Cipher(algorithms.AES(key.encode()), modes.CBC(init_vector.encode()), backend=default_backend())
            encryptor = cipher.encryptor()
            message = message.encode()

            padded_data = self.pkcs5_padding(message, 16)
            ciphertext = encryptor.update(padded_data) # + encryptor.finalize()
            ciphertext = init_vector.encode() + ciphertext

            return base64.b64encode(ciphertext).decode()
        
        except Exception as e:
            logger.error("An error occurred while encrypting: %s", e)
            return None


    def decrypt_key(self, b64_encrypted_msg: str, private_key) -> str:
        try:
            encrypted_msg = b64decode(b64_encrypted_msg)
            decrypted_msg = self.rsa_decrypt(encrypted_msg, private_key)
     
            return decrypted_msg.decode('utf-8')
        except Exception as e:
            raise Exception(f"Error decrypting message: {e}")

    def decrypt_data(self, encrypted_str: str, key: str) -> Optional[str]:
        try:
            encrypted = base64.b64decode(encrypted_str)
            iv = encrypted[:16]  # Extract IV (first 16 bytes)
            ciphertext = encrypted[16:]  # Extract ciphertext (remaining bytes)

            # Key must be bytes
            key_bytes = key.encode('utf-8')  # Assuming UTF-8 encoding, adjust if needed

            key_length = len(key_bytes)
            if key_length not in (16, 24, 32):
                raise ValueError("Invalid AES key length. Key must be 16, 24, or 32 bytes.")


            iv_parameter_spec = modes.CBC(iv)  # Use CBC mode
            cipher = Cipher(algorithms.AES(key_bytes), iv_parameter_spec, backend=default_backend())
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            decrypted_data = self.pkcs5_unpadding(plaintext)

            return decrypted_data.decode('utf-8')  # Decode bytes to string

        except Exception as e:
            raise ValueError(f"An error occurred while decrypting: {e}")


    def generate_sha512_hash(self, input: str) -> str:
        try:
            digest = hashlib.sha512()  # Replace with the desired hash algorithm (e.g., sha1, md5)
            digest.update(input.encode('utf-8'))
            hashed_bytes = digest.digest()
            return self.bytes_to_hexlify(hashed_bytes)  # Convert bytes to hexadecimal string
        except Exception as e:
            raise Exception(f"Error hashing string: {e}")
    
    def bytes_to_hexlify(self, hash_bytes):
        """Converts bytes to a hexadecimal string (similar to Java's bytesToHex)."""
        # Method 1 (using binascii.hexlify - recommended):
        hex_string = binascii.hexlify(hash_bytes).decode('utf-8') # Decode from bytes to string
        return hex_string

    def generate_random_key(self, key_length: int) -> str:
        try:
            char_set = AppConstants.CHAR_SET 

            # Create the random key using the defined character set
            key_builder = ''.join(random.choice(char_set) for _ in range(key_length))
            return key_builder
        except Exception as e:
            raise Exception(f"Error generating random key: {e}")
        
    def generate_xid_fingerprint_header(self, payload, api_key, server_public_key_path):
        """
        Generates an XID fingerprint header using SHA512 hashing and encryption.

        Args:
            payload: The payload string.
            api_key: The API key.
            server_public_key_path: Path to the server's public key file (PEM format).

        Returns:
            The encrypted XID fingerprint header string.

        Raises:
            SDKClientException: If an error occurs during fingerprint generation or encryption.
        """

        try:
            # Generate SHA512 hash
            sha512_hash = self.generate_sha512_hash(payload)
            # Combine data with delimiter
            id_fingerprint = "|".join([ api_key, sha512_hash])
            # print(f"idFingerprint: {id_fingerprint}")  # Replace with debug logging

            base64_decoded_fingerprint = id_fingerprint.encode().decode()


            encrypted_fingerprint = self.encrypt_key(base64_decoded_fingerprint, self.load_public_key(server_public_key_path))
            
            return encrypted_fingerprint

        except ( InvalidSignature, UnsupportedAlgorithm) as e:
            logger.error(f"Error generating or encrypting fingerprint: {e}")
            raise SDKClientException("Fingerprint generation or encryption failed.")

