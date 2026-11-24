import os
import uuid

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.mongo import ensure_indexes


@pytest.fixture(scope="session")
def mongo_client():
    client = MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except PyMongoError:
        if os.getenv("CI"):  # in CI a missing Mongo is a failure, not a skip
            raise
        pytest.skip("MongoDB not reachable (run: docker compose up -d mongo)")
    yield client
    client.close()


@pytest.fixture
def events_col(mongo_client):
    """A throwaway database per test, so dev data is never touched."""
    name = f"sentineliq_test_{uuid.uuid4().hex[:8]}"
    col = mongo_client[name]["events"]
    ensure_indexes(col)
    yield col
    mongo_client.drop_database(name)