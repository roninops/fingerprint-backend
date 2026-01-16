import os
from dotenv import load_dotenv

load_dotenv()

FINGERPRINT_DB_URL = os.getenv("FINGERPRINT_DB_URL")
JOURNAL_DB_URL = os.getenv("JOURNAL_DB_URL")
