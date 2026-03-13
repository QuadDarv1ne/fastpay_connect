"""Tests for database and dependencies."""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from app.database import check_db_connection, engine
from app.dependencies import get_db, verify_db_connection


class TestDatabaseConnection:
    def test_check_db_connection_success(self):
        result = check_db_connection()
        assert result is True

    def test_check_db_connection_failure(self, mocker):
        mocker.patch("app.database.engine.connect", side_effect=Exception("Connection failed"))
        result = check_db_connection()
        assert result is False


class TestGetDb:
    def test_get_db_success(self):
        db_gen = get_db()
        db = next(db_gen)
        assert db is not None
        try:
            next(db_gen)
        except StopIteration:
            pass


class TestVerifyDbConnection:
    @pytest.mark.asyncio
    async def test_verify_db_connection_success(self):
        result = await verify_db_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_db_connection_failure(self, mocker):
        mocker.patch("app.dependencies.check_db_connection", return_value=False)
        with pytest.raises(HTTPException) as exc_info:
            await verify_db_connection()
        assert exc_info.value.status_code == 503
        assert "Database connection failed" in str(exc_info.value.detail)


class TestDatabaseEngine:
    def test_engine_url(self):
        from app.database import get_engine_url
        from app.settings import settings
        url = get_engine_url()
        assert url is not None

    def test_database_tables_exist(self):
        from app.database import Base
        from app.models.payment import Payment
        assert "payments" in Base.metadata.tables
