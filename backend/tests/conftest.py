import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DEMO_LOGIN_ENABLED", "true")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-please-use-long-value")
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-use-long-value")

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.bootstrap import seed


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Testing = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    db = Testing()
    seed(db)
    db.close()

    def _get_db():
        session = Testing()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
