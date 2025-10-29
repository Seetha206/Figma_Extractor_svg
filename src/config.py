import os
from typing import Optional

class Config:
    """Configuration management using environment variables"""
    
    def __init__(self):
        # Figma configuration
        self.figma_token = os.getenv('FIGMA_API_TOKEN')
        
        # DigitalOcean Spaces configuration
        self.do_access_key = os.getenv('DO_ACCESS_KEY')
        self.do_secret_key = os.getenv('DO_SECRET_KEY')
        self.do_region = os.getenv('DO_REGION', 'nyc3')
        self.do_space_name = os.getenv('DO_SPACE_NAME')
        
        # Optional configurations
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    def validate(self) -> bool:
        """Validate that required configuration is present"""
        required_vars = [
            ('FIGMA_API_TOKEN', self.figma_token),
            ('DO_ACCESS_KEY', self.do_access_key),
            ('DO_SECRET_KEY', self.do_secret_key),
            ('DO_SPACE_NAME', self.do_space_name)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    def get_do_endpoint_url(self) -> str:
        """Get DigitalOcean Spaces endpoint URL"""
        return f'https://{self.do_region}.digitaloceanspaces.com'