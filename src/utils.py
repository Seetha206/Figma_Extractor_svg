import re
import logging
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    invalid_chars = r'[<>:"/\\|?*&]'
    sanitized = re.sub(invalid_chars, '_', filename)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    
    if not sanitized:
        sanitized = "figma_export"
    
    return sanitized

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )