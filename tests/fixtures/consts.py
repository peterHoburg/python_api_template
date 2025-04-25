import os
import uuid

# Test database configuration
TEST_DB_HOST = os.environ.get("TEST_POSTGRES_HOST", "localhost")
TEST_DB_PORT = os.environ.get("TEST_POSTGRES_PORT", "5432")
TEST_DB_USER = os.environ.get("TEST_POSTGRES_USER", "admin")
TEST_DB_PASSWORD = os.environ.get("TEST_POSTGRES_PASSWORD", "root")
TEST_DB_URL = f"postgresql+psycopg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/FAKE"

# Test data
FAKE_USER_UUID = uuid.UUID("8dd4ab9a-d0cc-4ba5-be19-1c79000a0a13")
