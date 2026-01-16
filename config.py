"""Agent configuration"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Security
    api_key: str
    allowed_ips: str = ""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8443
    
    # OpenVPN Access Server
    sacli_path: str = "/usr/local/openvpn_as/scripts/sacli"
    admin_ui_url: str = "https://localhost:943"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def allowed_ip_list(self) -> List[str]:
        """Parse allowed IPs from comma-separated string"""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(",") if ip.strip()]


settings = Settings()