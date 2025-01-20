# load the environment variables using python-dotenv
import os
from dotenv import load_dotenv
import json

# Load .env file if it exists (local development)
if os.path.exists(".env"):
    load_dotenv()

# Configuration variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PARENT = os.getenv('PARENT')

# Handle Google Cloud credentials
def setup_google_credentials():
    # For local development
    if os.path.exists('aagam-translation-2.json'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'aagam-translation-2.json'
    # For Cloud Run
    elif os.getenv('GOOGLE_CLOUD_CREDENTIALS'):
        creds_dict = json.loads(os.getenv('GOOGLE_CLOUD_CREDENTIALS'))
        creds_path = '/tmp/google-credentials.json'
        with open(creds_path, 'w') as f:
            json.dump(creds_dict, f)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path

setup_google_credentials()