"""
ICICI Eazypay SDK Client Wrapper

This module provides a wrapper around the ICICI Eazypay SDK for generating QR codes
and checking transaction status. It handles the initialization of the SDK with
Django settings and provides a clean interface for the payment views.

Required Django Settings (loaded from .env via python-decouple):
    - ICICI_ENABLED: Enable ICICI payments (bool)
    - ICICI_ENV_TYPE: "UAT" for sandbox or "PROD" for production
    - ICICI_MERCHANT_ID: ICICI Merchant ID
    - ICICI_TERMINAL_ID: Terminal ID for the POS
    - ICICI_API_KEY: The API key for ICICI Eazypay (maps to EAZYPAY_API_KEY)
    - ICICI_KEYSTORE_PATH: Path to the .p12 keystore file
    - ICICI_KEYSTORE_PASSWORD: Password for the keystore
    - ICICI_KEYSTORE_ALIAS: Alias for the private key (default: "ICICI")
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)

# SDK availability flag
SDK_AVAILABLE = False

# Set up default environment variables for SDK initialization
# The SDK reads these from os.environ, so we set placeholders here
# and update them from Django settings when configure() is called
os.environ.setdefault('ENV_TYPE', 'UAT')
os.environ.setdefault('EAZYPAY_API_KEY', 'placeholder')
os.environ.setdefault('EAZYPAY_KEYSTORE_PATH', '/dev/null')
os.environ.setdefault('EAZYPAY_KEYSTORE_PASSWORD', 'placeholder')
os.environ.setdefault('EAZYPAY_KEYSTORE_ALIAS', 'ICICI')
os.environ.setdefault('APPLICATION_JSON_CHARSET_UTF_8', 'application/json; charset=utf-8')
os.environ.setdefault('API_KEY', 'apiKey')
os.environ.setdefault('SHA_512', 'SHA-512')
os.environ.setdefault('X_ID_FINGERPRINT', 'X-ID-Fingerprint')
os.environ.setdefault('X_PRIORITY_HEADER', 'X-Priority')
os.environ.setdefault('ASYMMETRIC_CYPHER_RSA', 'RSA/ECB/PKCS1Padding')
os.environ.setdefault('SYMMETRIC_CYPHER_AES', 'AES/CBC/PKCS5Padding')
os.environ.setdefault('AES', 'AES')
os.environ.setdefault('CHAR_SET', 'abcdefghijklmnopqrstuvwxyz')
os.environ.setdefault('KEY_LENGTH', '32')
os.environ.setdefault('IV_KEY_LENGTH', '16')
os.environ.setdefault('WITH_RESPONSE_MODELS', 'false')

# Try to import SDK components
try:
    from httpcore.AppConstants import load_dotenv_from_path
    from eazypay.api import qr3, transaction_status
    from eazypay.model.request.QR3RequestDTO import QR3RequestDTO
    from eazypay.model.request.TransactionStatusRequestDTO import TransactionStatusRequestDTO
    SDK_AVAILABLE = True
    logger.info("Eazypay SDK loaded successfully")
except ImportError as e:
    logger.warning(f"Eazypay SDK not available: {e}")
    SDK_AVAILABLE = False


class ICICIClient:
    """
    Client for interacting with ICICI Eazypay APIs.
    
    This client wraps the Eazypay SDK and provides methods for:
    - Generating dynamic QR codes for UPI payments
    - Checking transaction status
    """
    
    def __init__(self):
        self.merchant_id: Optional[str] = None
        self.terminal_id: Optional[str] = None
        self.sub_merchant_id: Optional[str] = None
        self._configured = False
        
    def configure(
        self,
        merchant_id: str,
        terminal_id: str,
        sub_merchant_id: str = "",
        env_type: str = "UAT",
        api_key: Optional[str] = None,
        keystore_path: Optional[str] = None,
        keystore_password: Optional[str] = None,
        keystore_alias: Optional[str] = None,
    ) -> None:
        """
        Configure the ICICI client with merchant credentials.
        
        Args:
            merchant_id: ICICI Merchant ID
            terminal_id: Terminal ID for the POS
            sub_merchant_id: Sub-merchant ID (optional)
            env_type: "UAT" for sandbox, "PROD" for production
            api_key: Eazypay API key
            keystore_path: Path to .p12 keystore
            keystore_password: Keystore password
            keystore_alias: Key alias
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("Eazypay SDK is not installed")
        
        # Set environment variables that the SDK reads
        os.environ["ENV_TYPE"] = env_type
        
        if api_key:
            os.environ["EAZYPAY_API_KEY"] = api_key
        if keystore_path:
            os.environ["EAZYPAY_KEYSTORE_PATH"] = keystore_path
        if keystore_password:
            os.environ["EAZYPAY_KEYSTORE_PASSWORD"] = keystore_password
        if keystore_alias:
            os.environ["EAZYPAY_KEYSTORE_ALIAS"] = keystore_alias
        
        # Validate required configuration
        required_settings = {
            "EAZYPAY_API_KEY": api_key or os.environ.get("EAZYPAY_API_KEY"),
            "EAZYPAY_KEYSTORE_PATH": keystore_path or os.environ.get("EAZYPAY_KEYSTORE_PATH"),
            "EAZYPAY_KEYSTORE_PASSWORD": keystore_password or os.environ.get("EAZYPAY_KEYSTORE_PASSWORD"),
            "EAZYPAY_KEYSTORE_ALIAS": keystore_alias or os.environ.get("EAZYPAY_KEYSTORE_ALIAS"),
        }
        
        missing = [key for key, value in required_settings.items() if not value or value == 'placeholder']
        if missing:
            raise ValueError(f"Missing required ICICI configuration: {', '.join(missing)}")
        
        self.merchant_id = merchant_id
        self.terminal_id = terminal_id
        self.sub_merchant_id = sub_merchant_id or merchant_id
        self._configured = True
        
        logger.info(f"ICICI client configured for merchant {merchant_id} in {env_type} mode")
    
    def generate_qr(
        self,
        amount: Decimal,
        merchant_tran_id: str,
        bill_number: Optional[str] = None,
        validity_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a dynamic QR code for UPI payment.
        
        Args:
            amount: Payment amount
            merchant_tran_id: Unique transaction ID (max 20 chars)
            bill_number: Bill/Order number (optional)
            validity_minutes: QR validity in minutes (default 5)
            
        Returns:
            Dictionary containing:
                - success: bool
                - qr_string: UPI QR code string (if success)
                - transaction_id: ICICI transaction reference
                - ref_id: ICICI reference ID
                - message: Response message
                - error: Error message (if failed)
        """
        if not self._configured:
            raise RuntimeError("ICICI client not configured. Call configure() first.")
        
        if not SDK_AVAILABLE:
            # Fallback for development/testing without SDK
            logger.warning("SDK not available, returning mock response")
            return self._mock_qr_response(amount, merchant_tran_id)
        
        try:
            # Format amount to 2 decimal places
            amount_str = f"{float(amount):.2f}"
            
            # Prepare request payload
            payload = {
                "terminalId": self.terminal_id,
                "amount": amount_str,
                "billNumber": bill_number or merchant_tran_id[:20],
                "merchantId": self.merchant_id,
                "merchantTranId": merchant_tran_id[:20],  # ICICI limit
            }
            
            logger.debug(f"Generating QR for amount {amount_str}, txn: {merchant_tran_id}")
            
            # Call SDK
            dto = QR3RequestDTO(**payload)
            response = qr3(dto)
            
            # Parse response
            result = {
                "success": response.success == "Y",
                "qr_string": response.response if response.success == "Y" else None,
                "transaction_id": response.merchantTranId,
                "ref_id": response.refId,
                "message": response.message,
                "error": response.errormessage if response.errormessage else None,
                "raw_response": response.model_dump() if hasattr(response, 'model_dump') else str(response)
            }
            
            if result["success"]:
                logger.info(f"QR generated successfully for txn: {merchant_tran_id}")
            else:
                logger.warning(f"QR generation failed: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating QR: {e}")
            return {
                "success": False,
                "qr_string": None,
                "transaction_id": merchant_tran_id,
                "ref_id": None,
                "message": "Error generating QR code",
                "error": str(e),
                "raw_response": None
            }
    
    def check_status(self, merchant_tran_id: str) -> Dict[str, Any]:
        """
        Check the status of a transaction.
        
        Args:
            merchant_tran_id: The transaction ID to check
            
        Returns:
            Dictionary containing:
                - success: bool (API call succeeded)
                - status: str - Payment status (SUCCESS, FAILURE, PENDING, etc.)
                - transaction_id: Merchant transaction ID
                - amount: Transaction amount
                - bank_rrn: Bank reference number (if available)
                - message: Response message
                - error: Error message (if failed)
        """
        if not self._configured:
            raise RuntimeError("ICICI client not configured. Call configure() first.")
        
        if not SDK_AVAILABLE:
            logger.warning("SDK not available, returning mock response")
            return self._mock_status_response(merchant_tran_id)
        
        try:
            payload = {
                "merchantId": self.merchant_id,
                "subMerchantId": self.sub_merchant_id,
                "terminalId": self.terminal_id,
                "merchantTranId": merchant_tran_id[:20],
            }
            
            logger.debug(f"Checking status for txn: {merchant_tran_id}")
            
            dto = TransactionStatusRequestDTO(**payload)
            response = transaction_status(dto)
            
            # Map ICICI status to our standard status
            icici_status = response.status.upper() if response.status else "UNKNOWN"
            status_map = {
                "SUCCESS": "SUCCESS",
                "FAILED": "FAILED",
                "FAILURE": "FAILED",
                "PENDING": "PENDING",
                "INITIATED": "PENDING",
                "EXPIRED": "EXPIRED",
            }
            
            result = {
                "success": response.success == "Y",
                "status": status_map.get(icici_status, "PENDING"),
                "transaction_id": response.merchantTranId,
                "amount": response.Amount,
                "bank_rrn": response.OriginalBankRRN if response.OriginalBankRRN else None,
                "message": response.message,
                "error": response.errormessage if response.errormessage else None,
                "umn": response.UMN if response.UMN else None,
                "raw_response": response.model_dump() if hasattr(response, 'model_dump') else str(response)
            }
            
            logger.debug(f"Status for {merchant_tran_id}: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "transaction_id": merchant_tran_id,
                "amount": None,
                "bank_rrn": None,
                "message": "Error checking transaction status",
                "error": str(e),
                "umn": None,
                "raw_response": None
            }
    
    def _mock_qr_response(self, amount: Decimal, merchant_tran_id: str) -> Dict[str, Any]:
        """Generate a mock QR response for testing without SDK."""
        import uuid
        mock_ref = f"ICICI{uuid.uuid4().hex[:12].upper()}"
        return {
            "success": True,
            "qr_string": f"upi://pay?pa=freshon@icici&pn=FreshOn&am={amount:.2f}&tr={merchant_tran_id}&cu=INR",
            "transaction_id": merchant_tran_id,
            "ref_id": mock_ref,
            "message": "Mock QR generated (SDK not available)",
            "error": None,
            "raw_response": None
        }
    
    def _mock_status_response(self, merchant_tran_id: str) -> Dict[str, Any]:
        """Generate a mock status response for testing without SDK."""
        return {
            "success": True,
            "status": "PENDING",
            "transaction_id": merchant_tran_id,
            "amount": None,
            "bank_rrn": None,
            "message": "Mock status (SDK not available)",
            "error": None,
            "umn": None,
            "raw_response": None
        }


# Singleton instance
_icici_client: Optional[ICICIClient] = None


def get_icici_client() -> ICICIClient:
    """Get or create the singleton ICICI client instance."""
    global _icici_client
    if _icici_client is None:
        _icici_client = ICICIClient()
    return _icici_client


def configure_from_settings():
    """
    Configure the ICICI client from Django settings (loaded from .env via python-decouple).
    
    This should be called during app initialization.
    """
    from django.conf import settings
    
    client = get_icici_client()
    
    # Check if ICICI is enabled in settings
    if not getattr(settings, 'ICICI_ENABLED', False):
        logger.info("ICICI payments not enabled in settings")
        return
    
    try:
        client.configure(
            merchant_id=settings.ICICI_MERCHANT_ID,
            terminal_id=settings.ICICI_TERMINAL_ID,
            sub_merchant_id=getattr(settings, 'ICICI_SUB_MERCHANT_ID', ''),
            env_type=getattr(settings, 'ICICI_ENV_TYPE', 'UAT'),
            api_key=settings.ICICI_API_KEY,
            keystore_path=settings.ICICI_KEYSTORE_PATH,
            keystore_password=settings.ICICI_KEYSTORE_PASSWORD,
            keystore_alias=getattr(settings, 'ICICI_KEYSTORE_ALIAS', 'ICICI'),
        )
        logger.info("ICICI client configured from settings")
    except Exception as e:
        logger.error(f"Failed to configure ICICI client: {e}")
        raise
