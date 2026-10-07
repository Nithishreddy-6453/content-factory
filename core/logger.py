import logging
import os
from core.config import config

def setup_logger(name: str) -> logging.Logger:
    os.makedirs(config.system_log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(os.path.join(config.system_log_dir, 'system.log'))
        fh.setLevel(logging.DEBUG)
        
        # Error file handler
        efh = logging.FileHandler(os.path.join(config.system_log_dir, 'error.log'))
        efh.setLevel(logging.ERROR)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        efh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(efh)
        logger.addHandler(ch)
        
    return logger

logger = setup_logger("ContentFactory")
