import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DATABASE = Path(tempfile.gettempdir()) / "paiguangguang-assistant-tests.db"
os.environ["ASSISTANT_DATABASE_URL"] = f"sqlite:///{TEST_DATABASE.as_posix()}"
os.environ["ASSISTANT_OWNER_COOKIE_SECRET"] = "test-secret-for-assistant-owner-cookie-32"

from app.db import Base, engine
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def empty_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
