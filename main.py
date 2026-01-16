"""FastAPI provisioning agent"""
from fastapi import FastAPI, Depends, Request, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.security import verify_api_key, verify_ip_address
from app.sacli_runner import SacliRunner
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VPN Provisioning Agent", version="1.0.0")


class ProvisionRequest(BaseModel):
    telegram_id: int
    desired_username: str


class ProvisionResponse(BaseModel):
    username: str
    password: str
    token_url: str
    ovpn_file_base64: str = None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"{request.method} {request.url.path} from {request.client.host}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


@app.get("/health")
async def health_check(
    api_key: str = Depends(verify_api_key)
):
    """Health check endpoint"""
    return {"status": "healthy", "service": "vpn-provisioning-agent"}


@app.post("/provision", response_model=ProvisionResponse)
async def provision_user(
    request: ProvisionRequest,
    api_key: str = Depends(verify_api_key),
    ip_check: bool = Depends(verify_ip_address)
):
    """
    Provision VPN user
    
    1. Ensures user exists in OpenVPN
    2. Sets local password
    3. Generates profile token URL
    4. Optionally returns .ovpn file
    """
    logger.info(f"Provisioning user: {request.desired_username} (Telegram ID: {request.telegram_id})")
    
    try:
        runner = SacliRunner()
        result = runner.provision_user(
            username=request.desired_username
        )
        
        if not result:
            logger.error(f"Provisioning failed for {request.desired_username}")
            raise HTTPException(
                status_code=500,
                detail="Failed to provision user in OpenVPN Access Server"
            )
        
        logger.info(f"Successfully provisioned {request.desired_username}")
        return ProvisionResponse(**result)
        
    except Exception as e:
        logger.error(f"Provisioning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VPN Provisioning Agent",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        ssl_keyfile="/etc/vpn-agent/key.pem",
        ssl_certfile="/etc/vpn-agent/cert.pem",
        reload=False
    )