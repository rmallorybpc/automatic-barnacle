"""Common utilities for feature monitoring."""
import logging
import time
from typing import Any, Callable, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up structured logging for a module.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Only add handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def create_session_with_retry(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (500, 502, 503, 504),
    timeout: int = 30
) -> requests.Session:
    """Create a requests session with retry logic.
    
    Args:
        retries: Number of retry attempts
        backoff_factor: Backoff multiplier between retries
        status_forcelist: HTTP status codes to retry on
        timeout: Request timeout in seconds
        
    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def safe_request(
    url: str,
    method: str = "GET",
    logger: Optional[logging.Logger] = None,
    **kwargs
) -> Optional[requests.Response]:
    """Make an HTTP request with retry logic and error handling.
    
    Args:
        url: URL to request
        method: HTTP method (GET, POST, etc.)
        logger: Logger instance for error reporting
        **kwargs: Additional arguments for requests
        
    Returns:
        Response object or None on failure
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    session = create_session_with_retry()
    
    try:
        logger.info(f"Making {method} request to {url}")
        response = session.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        logger.info(f"Request successful: {response.status_code}")
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url} - {str(e)}")
        return None
    finally:
        session.close()


def validate_file_exists(filepath: str, logger: Optional[logging.Logger] = None) -> bool:
    """Validate that a required file exists.
    
    Args:
        filepath: Path to file
        logger: Logger instance for error reporting
        
    Returns:
        True if file exists, False otherwise
    """
    import os
    if logger is None:
        logger = logging.getLogger(__name__)
    
    if not os.path.exists(filepath):
        logger.error(f"Required file not found: {filepath}")
        return False
    return True


def safe_write_file(
    filepath: str,
    content: str,
    logger: Optional[logging.Logger] = None
) -> bool:
    """Safely write content to a file with error handling.
    
    Args:
        filepath: Path to output file
        content: Content to write
        logger: Logger instance for error reporting
        
    Returns:
        True on success, False on failure
    """
    import os
    if logger is None:
        logger = logging.getLogger(__name__)
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write to temporary file first
        temp_filepath = f"{filepath}.tmp"
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Atomic rename
        os.replace(temp_filepath, filepath)
        logger.info(f"Successfully wrote file: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to write file {filepath}: {str(e)}")
        return False
