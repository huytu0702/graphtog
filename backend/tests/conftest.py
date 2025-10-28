"""
Pytest configuration and shared fixtures
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.postgres import Base, get_db
from app.main import app


# Test database configuration
SQLALCHEMY_TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://graphtog_user:graphtog_password@localhost:5432/graphtog_db"
)

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        yield
        # Don't drop tables to preserve data for debugging
        # Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"\n⚠️  Database setup warning: {e}")
        print(f"   DATABASE_URL: {SQLALCHEMY_TEST_DATABASE_URL}")
        print("   Make sure PostgreSQL is running via docker-compose")
        yield


@pytest.fixture
def db():
    """Create a new database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db) -> TestClient:
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def auth_token(client) -> str:
    """Create a test user and get auth token"""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
    }

    # Register user
    response = client.post("/api/auth/register", json=user_data)
    if response.status_code != 200:
        pytest.skip(f"Could not create test user: {response.text}")

    # Login
    response = client.post(
        "/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]}
    )
    if response.status_code != 200:
        pytest.skip(f"Could not login: {response.text}")

    return response.json()["access_token"]


@pytest.fixture
def authenticated_client(client, auth_token) -> TestClient:
    """FastAPI test client with authentication"""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client
