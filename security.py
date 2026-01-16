"""Security middleware and utilities"""
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from app.config import settings
import logging

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from header"""
    if not api_key:
        logger.warning("Missing API key")
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if api_key != settings.api_key:
        logger.warning(f"Invalid API key: {api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key


async def verify_ip_address(request: Request):
    """Verify client IP is in allowlist"""
    if not settings.allowed_ip_list:
        # No IP restriction if list is empty
        return True
    
    client_ip = request.client.host
    
    if client_ip not in settings.allowed_ip_list:
        logger.warning(f"Unauthorized IP: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail="IP address not authorized"
        )
    
    return True