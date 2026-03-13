"""Tests for email service."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.email_service import EmailService, email_service


class TestEmailService:
    def test_email_service_disabled(self):
        service = EmailService()
        service.enabled = False
        import asyncio
        result = asyncio.run(service.send_payment_notification(
            to_email="test@example.com",
            payment_id="pay_123",
            amount=100.0,
            status="completed",
            description="Test"
        ))
        assert result is False

    def test_email_service_incomplete_config(self):
        service = EmailService()
        service.enabled = True
        service.smtp_server = None
        import asyncio
        result = asyncio.run(service.send_payment_notification(
            to_email="test@example.com",
            payment_id="pay_123",
            amount=100.0,
            status="completed",
            description="Test"
        ))
        assert result is False

    @patch('smtplib.SMTP')
    def test_send_payment_notification_success(self, mock_smtp):
        service = EmailService()
        service.enabled = True
        service.smtp_server = "smtp.example.com"
        service.smtp_port = 587
        service.username = "user"
        service.password = "pass"
        service.from_email = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        import asyncio
        result = asyncio.run(service.send_payment_notification(
            to_email="test@example.com",
            payment_id="pay_123",
            amount=100.0,
            status="completed",
            description="Test"
        ))
        assert result is True
        mock_server.send_message.assert_called_once()

    @patch('smtplib.SMTP')
    def test_send_payment_notification_failure(self, mock_smtp):
        service = EmailService()
        service.enabled = True
        service.smtp_server = "smtp.example.com"
        service.smtp_port = 587
        service.username = "user"
        service.password = "pass"
        service.from_email = "noreply@example.com"

        mock_smtp.side_effect = Exception("Connection failed")

        import asyncio
        result = asyncio.run(service.send_payment_notification(
            to_email="test@example.com",
            payment_id="pay_123",
            amount=100.0,
            status="completed",
            description="Test"
        ))
        assert result is False

    @patch('smtplib.SMTP')
    def test_send_bulk_notification(self, mock_smtp):
        service = EmailService()
        service.enabled = True
        service.smtp_server = "smtp.example.com"
        service.smtp_port = 587
        service.username = "user"
        service.password = "pass"
        service.from_email = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        import asyncio
        result = asyncio.run(service.send_bulk_notification(
            emails=["test1@example.com", "test2@example.com"],
            subject="Test",
            body="Test body"
        ))
        assert result == 2
        assert mock_server.send_message.call_count == 2
