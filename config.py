# config.py
import os
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('banking_bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Application constants
APP_NAME = "banking_bot"
DEFAULT_USER_ID = "anonymous"
SESSION_TYPE = os.getenv("SESSION_TYPE", "memory")  # "memory" or "sqlite"
SESSION_DB_PATH = os.getenv("SESSION_DB_PATH", "data/banking_sessions.db")
SESSION_TTL = int(os.getenv("SESSION_TTL", "3600"))  # 1 hour default

# API Keys - IMPORTANT: Use environment variables for security
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY")
}

# Model configurations
MODELS = {
    "root_agent": os.getenv("ROOT_AGENT_MODEL", "openai/gpt-4o"),
    "greeting_agent": os.getenv("GREETING_AGENT_MODEL", "openai/gpt-4o"),
    "farewell_agent": os.getenv("FAREWELL_AGENT_MODEL", "openai/gpt-4o"),
    "balance_agent": os.getenv("BALANCE_AGENT_MODEL", "openai/gpt-4o"),
    "transfer_agent": os.getenv("TRANSFER_AGENT_MODEL", "openai/gpt-4o")
}

# Banking Bot specific configurations
BANKING_CONFIG = {
    # Transfer limits
    "max_transfer_amount": float(os.getenv("MAX_TRANSFER_AMOUNT", "1000.0")),
    "daily_transfer_limit": float(os.getenv("DAILY_TRANSFER_LIMIT", "5000.0")),
    
    # Security settings
    "authentication_required": os.getenv("AUTH_REQUIRED", "true").lower() == "true",
    "blocked_keywords": os.getenv("BLOCKED_KEYWORDS", "password,ssn,social security,pin").split(","),
    "restricted_accounts": os.getenv("RESTRICTED_ACCOUNTS", "business,corporate,trust").split(","),
    
    # Session settings
    "session_idle_timeout": int(os.getenv("SESSION_IDLE_TIMEOUT", "900")),  # 15 minutes
    
    # UI/UX settings
    "welcome_message": os.getenv(
        "WELCOME_MESSAGE", 
        "Welcome to Banking Assistant! How can I help you today?"
    ),
    "authentication_message": os.getenv(
        "AUTH_MESSAGE",
        "Please authenticate to access banking services."
    )
}

# FastAPI settings
API_CONFIG = {
    "host": os.getenv("API_HOST", "0.0.0.0"),
    "port": int(os.getenv("API_PORT", "8000")),
    "debug": os.getenv("API_DEBUG", "false").lower() == "true",
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
    "api_prefix": os.getenv("API_PREFIX", "/api")
}

def validate_config() -> bool:
    """
    Validate the configuration to ensure all required settings are present.
    
    Returns:
        bool: True if config is valid, raises exception otherwise
    """
    # Check for API keys
    missing_keys = []
    for provider, key in API_KEYS.items():
        if provider in MODELS.values() and not key:
            missing_keys.append(provider)
    
    if missing_keys:
        logger.warning(f"Missing API keys for providers: {', '.join(missing_keys)}")
        if any(model.startswith(f"{provider}/") for provider in missing_keys for model in MODELS.values()):
            raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")
    
    # Check for SQLite directory if using SQLite sessions
    if SESSION_TYPE == "sqlite":
        db_dir = os.path.dirname(SESSION_DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created directory for SQLite database: {db_dir}")
            except Exception as e:
                raise ValueError(f"Failed to create SQLite database directory: {e}")
    
    logger.info("Configuration validated successfully")
    return True

def get_model_provider(model_name: str) -> str:
    """
    Extract the provider from a model name.
    
    Args:
        model_name: The model name, possibly with provider prefix
        
    Returns:
        str: The provider name
    """
    if "/" in model_name:
        return model_name.split("/")[0]
    return "google"  # Default to Google if no provider specified

def display_config() -> Dict[str, Any]:
    """
    Get a sanitized version of the configuration for display/logging.
    
    Returns:
        Dict[str, Any]: Sanitized configuration
    """
    # Create a copy to avoid modifying the original
    display = {
        "app_name": APP_NAME,
        "session_type": SESSION_TYPE,
        "models": {k: v for k, v in MODELS.items()},
        "banking_config": {k: v for k, v in BANKING_CONFIG.items() if k not in ["blocked_keywords", "restricted_accounts"]},
        "api_config": {k: v for k, v in API_CONFIG.items()},
    }
    
    # Replace API keys with status
    display["api_keys"] = {
        provider: "configured" if key else "missing"
        for provider, key in API_KEYS.items()
    }
    
    return display

# Validate configuration on import
try:
    validate_config()
    logger.info(f"Configuration loaded: {display_config()}")
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise