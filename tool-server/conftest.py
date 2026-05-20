import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    # Point DB to a temp file for the entire test session
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    import database
    database.DB_PATH = db_path
    # Now import and init app AFTER patching
    from main import app
    from database import init_db
    init_db()
    with TestClient(app) as c:
        yield c
