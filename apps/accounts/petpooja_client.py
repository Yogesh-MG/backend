"""
Petpooja Payroll API Client

This module provides a client for interacting with the Petpooja Payroll API
to fetch employee attendance punch data.

API Documentation: https://developer.petpooja.com/

Required Django Settings (loaded from .env via python-decouple):
    - PETPOOJA_BASE_URL: Base URL for Petpooja API
    - PETPOOJA_CLIENT_ID: OAuth client ID
    - PETPOOJA_CLIENT_SECRET: OAuth client secret
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache keys
CACHE_KEY_ACCESS_TOKEN = "petpooja_access_token"
CACHE_KEY_REFRESH_TOKEN = "petpooja_refresh_token"
CACHE_KEY_TOKEN_EXPIRY = "petpooja_token_expiry"

# Default cache TTL (in seconds)
ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 86400  # 24 hours


class PetpoojaAPIError(Exception):
    """Base exception for Petpooja API errors."""
    pass


class PetpoojaAuthError(PetpoojaAPIError):
    """Exception for authentication errors."""
    pass


class PetpoojaClient:
    """
    Client for Petpooja Payroll API.
    
    Handles OAuth authentication, token caching, and API calls.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'PETPOOJA_BASE_URL', '')
        self.client_id = getattr(settings, 'PETPOOJA_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'PETPOOJA_CLIENT_SECRET', '')
        
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise PetpoojaAPIError("Petpooja API credentials not configured")
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _get_access_token(self) -> str:
        """
        Get a valid access token from cache or request a new one.
        
        Returns:
            str: Valid access token
        
        Raises:
            PetpoojaAuthError: If authentication fails
        """
        # Try to get token from cache
        access_token = cache.get(CACHE_KEY_ACCESS_TOKEN)
        token_expiry = cache.get(CACHE_KEY_TOKEN_EXPIRY)
        
        if access_token and token_expiry:
            # Check if token is still valid (with 5 minute buffer)
            if token_expiry > datetime.now() + timedelta(minutes=5):
                logger.debug("Using cached access token")
                return access_token
        
        # Token expired or not found, try to refresh
        refresh_token = cache.get(CACHE_KEY_REFRESH_TOKEN)
        if refresh_token:
            try:
                return self._refresh_access_token(refresh_token)
            except PetpoojaAuthError:
                logger.warning("Token refresh failed, requesting new token")
        
        # Request new token
        return self._request_new_token()
    
    def _request_new_token(self) -> str:
        """
        Request a new access token using client credentials.
        
        Returns:
            str: New access token
        """
        url = f"{self.base_url}/oauth/token"
        
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'payroll:read'  # Adjust scope as needed
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in', ACCESS_TOKEN_TTL)
            
            if not access_token:
                raise PetpoojaAuthError("No access token in response")
            
            # Cache tokens
            cache.set(CACHE_KEY_ACCESS_TOKEN, access_token, timeout=expires_in)
            if refresh_token:
                cache.set(CACHE_KEY_REFRESH_TOKEN, refresh_token, timeout=REFRESH_TOKEN_TTL)
            cache.set(
                CACHE_KEY_TOKEN_EXPIRY, 
                datetime.now() + timedelta(seconds=expires_in),
                timeout=expires_in
            )
            
            logger.info("Successfully obtained new access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise PetpoojaAuthError(f"Authentication failed: {e}")
    
    def _refresh_access_token(self, refresh_token: str) -> str:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            str: New access token
        """
        url = f"{self.base_url}/oauth/token"
        
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            access_token = data.get('access_token')
            new_refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in', ACCESS_TOKEN_TTL)
            
            if not access_token:
                raise PetpoojaAuthError("No access token in refresh response")
            
            # Cache new tokens
            cache.set(CACHE_KEY_ACCESS_TOKEN, access_token, timeout=expires_in)
            if new_refresh_token:
                cache.set(CACHE_KEY_REFRESH_TOKEN, new_refresh_token, timeout=REFRESH_TOKEN_TTL)
            cache.set(
                CACHE_KEY_TOKEN_EXPIRY,
                datetime.now() + timedelta(seconds=expires_in),
                timeout=expires_in
            )
            
            logger.info("Successfully refreshed access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise PetpoojaAuthError(f"Token refresh failed: {e}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
        
        Returns:
            dict: JSON response data
        """
        url = f"{self.base_url}{endpoint}"
        access_token = self._get_access_token()
        
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        
        try:
            response = self.session.request(method, url, headers=headers, **kwargs)
            
            # Handle token expiration (401)
            if response.status_code == 401:
                logger.warning("Access token expired, refreshing...")
                cache.delete(CACHE_KEY_ACCESS_TOKEN)
                access_token = self._get_access_token()
                headers['Authorization'] = f'Bearer {access_token}'
                response = self.session.request(method, url, headers=headers, **kwargs)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise PetpoojaAPIError(f"Request failed: {e}")
    
    def fetch_daily_punches(self, start_date: date, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Fetch attendance punch data from Petpooja API.
        
        Args:
            start_date: Start date for punch data
            end_date: End date for punch data (defaults to start_date)
        
        Returns:
            list: List of punch records
        
        Example response format:
        [
            {
                "emp_id": "EMP001",
                "payroll_date": "2025-09-01",
                "punch_data": [
                    {
                        "operation": "In",
                        "time": "09:00:00"
                    },
                    {
                        "operation": "Out",
                        "time": "18:00:00"
                    }
                ]
            }
        ]
        """
        if end_date is None:
            end_date = start_date
        
        endpoint = "/attendance/punches"
        
        payload = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        logger.info(f"Fetching punches from {start_date} to {end_date}")
        
        try:
            response = self._make_request('POST', endpoint, json=payload)
            
            # Extract punch data from response
            # Adjust based on actual API response structure
            punch_data = response.get('data', [])
            
            logger.info(f"Fetched {len(punch_data)} employee punch records")
            return punch_data
            
        except PetpoojaAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching punches: {e}")
            raise PetpoojaAPIError(f"Failed to fetch punches: {e}")
    
    def fetch_employees(self) -> List[Dict[str, Any]]:
        """
        Fetch employee list from Petpooja.
        
        Returns:
            list: List of employee records
        """
        endpoint = "/employees"
        
        try:
            response = self._make_request('GET', endpoint)
            return response.get('data', [])
        except PetpoojaAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching employees: {e}")
            raise PetpoojaAPIError(f"Failed to fetch employees: {e}")


# Singleton instance
_petpooja_client: Optional[PetpoojaClient] = None


def get_petpooja_client() -> PetpoojaClient:
    """Get or create the singleton Petpooja client instance."""
    global _petpooja_client
    if _petpooja_client is None:
        _petpooja_client = PetpoojaClient()
    return _petpooja_client
