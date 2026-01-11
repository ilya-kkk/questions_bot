import os
import sys

# Ensure the repository root is on sys.path for local imports.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Set deterministic env vars for config import during tests.
os.environ["BOT_TOKEN"] = "test-token"
os.environ["POSTGRES_DB"] = "app_db"
os.environ["POSTGRES_USER"] = "app_user"
os.environ["POSTGRES_PASSWORD"] = "password"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
