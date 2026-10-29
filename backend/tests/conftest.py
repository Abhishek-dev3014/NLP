import os
import tempfile
from pathlib import Path
import pytest

_temp = tempfile.TemporaryDirectory(prefix="verifact-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_temp.name) / 'tests.db'}"
os.environ["SESSION_SECRET"] = "test-only-session-secret-32-characters-long"
from fastapi.testclient import TestClient
from app.main import app, buckets
from app.db.session import Base, engine


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.create_all(engine)
    buckets.clear()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
