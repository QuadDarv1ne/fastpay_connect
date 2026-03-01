import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment variables BEFORE importing app modules
os.environ["YOOKASSA_SECRET_KEY"] = "test_secret_key"
os.environ["YOOKASSA_API_KEY"] = "test_api_key"
os.environ["TINKOFF_SECRET_KEY"] = "test_secret_key"
os.environ["TINKOFF_API_KEY"] = "test_api_key"
os.environ["CLOUDPAYMENTS_API_KEY"] = "test_api_key"
os.environ["UNITPAY_SECRET_KEY"] = "test_secret_key"
os.environ["UNITPAY_API_KEY"] = "test_api_key"
os.environ["ROBOKASSA_SECRET_KEY"] = "test_secret_key"
os.environ["ROBOKASSA_API_KEY"] = "test_api_key"
os.environ["SECRET_KEY"] = "test_secret_key"

from app.database import Base, get_db
from app.main import app
from typing import Generator

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
