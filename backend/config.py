import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# LLM API settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # Options: openai, anthropic, mistral
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")

# Log parser settings
LOG_PARSER_TYPE = os.getenv("LOG_PARSER_TYPE", "mavlink")  # Options: mavlink, dataflash