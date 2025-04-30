import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Cloud settings
PROJECT_ID = os.getenv('PROJECT_ID')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Agent settings
LEADS_FILE = 'leads.csv'
FOLLOW_UP_DELAY_HOURS = 24
LANGUAGE_CODE = 'en-US'

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Validation
if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable is not set")
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set") 