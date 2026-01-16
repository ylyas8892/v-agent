"""sacli command runner for OpenVPN Access Server"""
import subprocess
import logging
import secrets
import string
from typing import Optional, Dict
from app.config import settings

logger = logging.getLogger(__name__)


class SacliRunner:
    """Executes sacli commands for OpenVPN Access Server management"""
    
    @staticmethod
    def run_sacli(command: list, use_sudo: bool = True) -> tuple[bool, str]:
        """
        Execute sacli command
        
        Args:
            command: List of command arguments
            use_sudo: Whether to use sudo
            
        Returns:
            (success: bool, output: str)
        """
        if use_sudo:
            full_command = ['sudo', settings.sacli_path] + command
        else:
            full_command = [settings.sacli_path] + command
        
        logger.info(f"Executing: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Command succeeded: {' '.join(command)}")
                return True, result.stdout.strip()
            else:
                logger.error(f"Command failed: {result.stderr}")
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            logger.error("Command timed out")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False, str(e)
    
    @staticmethod
    def generate_password(length: int = 16) -> str:
        """Generate secure password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def ensure_user_exists(self, username: str) -> bool:
        """
        Ensure VPN user exists
        
        Uses UserPropPut with type=user_connect
        """
        success, output = self.run_sacli([
            '--user', username,
            'UserPropPut',
            'type',
            'user_connect'
        ])
        
        if success:
            logger.info(f"User {username} configured")
            return True
        else:
            logger.error(f"Failed to configure user {username}: {output}")
            return False
    
    def set_password(self, username: str, password: str) -> bool:
        """
        Set local password for user
        """
        success, output = self.run_sacli([
            '--user', username,
            '--new_pass', password,
            'SetLocalPassword',
        ])
        
        if success:
            logger.info(f"Password set for user {username}")
            return True
        else:
            logger.error(f"Failed to set password for {username}: {output}")
            return False
    
    import re

    def generate_profile_token(self, username: str) -> Optional[str]:
        success, output = self.run_sacli(['--user', username, 'AddProfileToken'])
        if not success:
            logger.error(f"Failed to generate token: {output}")
            return None

        # Вариант 1: openvpn://import-profile/https://....
        m = re.search(r"openvpn://import-profile/(https://\S+)", output)
        if m:
            return m.group(1)

        # Вариант 2: Token: <token>
        m = re.search(r"Token:\s*(\S+)", output)
        if m:
            token = m.group(1)
            return f"{settings.admin_ui_url}/?src=connect&username={username}&token={token}"

        logger.error(f"Token not found in output: {output}")
        return None

    
    def get_user_profile(self, username: str) -> Optional[str]:
        """
        Get .ovpn profile content using GetUserlogin
        
        Returns base64-encoded .ovpn content
        """
        import base64
        
        success, output = self.run_sacli([
            '--user', username,
            'GetUserlogin'
        ])
        
        if success:
            # Encode to base64 for transport
            encoded = base64.b64encode(output.encode()).decode()
            logger.info(f"Retrieved profile for {username}")
            return encoded
        else:
            logger.error(f"Failed to get profile: {output}")
            return None
    
    def provision_user(
        self,
        username: str,
        password: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Complete user provisioning workflow
        
        Returns:
            {
                'username': str,
                'password': str,
                'token_url': str,
                'ovpn_file_base64': str
            }
        """
        # Generate password if not provided
        if not password:
            password = self.generate_password()
        
        # Step 1: Ensure user exists
        if not self.ensure_user_exists(username):
            return None
        
        # Step 2: Set password
        if not self.set_password(username, password):
            return None
        
        # Step 3: Generate token URL
        token_url = self.generate_profile_token(username)
        if not token_url:
            logger.warning(f"Failed to generate token URL for {username}")
            # Continue anyway, we have credentials
        
        # Step 4: Get .ovpn file (optional)
        ovpn_file = self.get_user_profile(username)
        
        result = {
            'username': username,
            'password': password,
            'token_url': token_url or f"{settings.admin_ui_url}/?src=connect",
        }
        
        if ovpn_file:
            result['ovpn_file_base64'] = ovpn_file
        
        logger.info(f"Successfully provisioned user {username}")
        return result
