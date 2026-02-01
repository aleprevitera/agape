"""Configuration for the SSM question generator pipeline."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_BASE_URL = "https://api.openai.com/v1"

# Generation settings
DEFAULT_BATCH_SIZE = 5  # Questions per API call
DEFAULT_COUNT = 10  # Default number of questions to generate
MAX_CONCURRENCY = 3  # Max concurrent API requests

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_DELAY_SECONDS = 1.0  # Delay between batches

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0

# Output settings
DEFAULT_OUTPUT_FILE = "domande_generate.jsonl"
