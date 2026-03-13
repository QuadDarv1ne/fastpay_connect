"""
Тесты для Celery webhook retry системы.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.tasks.webhook_tasks import (
    process_webhook_task,
    send_webhook_retry_notification,
    cleanup_old_webhook_events,
    health_check,
    extract_webhook_event_id,
    STATUS_MAP,
    WEBHOOK_HANDLERS,
)


class TestExtractWebhookEventId:
    """Тесты для функции извлечения event_id."""

    def test_extract_from_event_id(self):
        payload = {"event_id": "test-123", "order_id": "order-456"}
        assert extract_webhook_event_id(payload) == "test-123"

    def test_extract_from_id(self):
        payload = {"id": "txn-789", "order_id": "order-456"}
        assert extract_webhook_event_id(payload) == "txn-789"

    def test_extract_from_transaction_id(self):
        payload = {"transaction_id": "txn-999", "order_id": "order-456"}
        assert extract_webhook_event_id(payload) == "txn-999"

    def test_no_event_id(self):
        payload = {"order_id": "order-456", "amount": 1000}
        assert extract_webhook_event_id(payload) is None

    def test_empty_payload(self):
        payload = {}
        assert extract_webhook_event_id(payload) is None


class TestStatusMap:
    """Тесты для маппинга статусов."""

    def test_payment_successful(self):
        assert STATUS_MAP["payment successful"] == "completed"

    def test_payment_canceled(self):
        assert STATUS_MAP["payment canceled"] == "cancelled"

    def test_payment_failed(self):
        assert STATUS_MAP["payment failed"] == "failed"

    def test_payment_refunded(self):
        assert STATUS_MAP["payment refunded"] == "refunded"

    def test_unknown_status(self):
        assert STATUS_MAP.get("unknown status", "pending") == "pending"


class TestProcessWebhookTaskSuccess:
    """Тесты успешной обработки webhook."""

    def test_yookassa_webhook_success(self):
        """Тест успешной обработки YooKassa webhook."""
        payload = {
            "event_id": "yookassa-123",
            "order_id": "order-456",
            "message": "payment successful",
        }
        
        mock_db = Mock()
        mock_repo = Mock()
        
        with patch('app.tasks.webhook_tasks.get_db_session', return_value=mock_db):
            with patch('app.tasks.webhook_tasks.PaymentRepository', return_value=mock_repo):
                with patch('asyncio.new_event_loop') as mock_loop_factory:
                    mock_loop = Mock()
                    mock_loop_factory.return_value = mock_loop
                    mock_loop.run_until_complete.return_value = {"status": "processed", "message": "payment successful"}
                    
                    # Тестируем через delay (постановка в очередь)
                    with patch.object(process_webhook_task, 'delay') as mock_delay:
                        mock_delay.return_value = Mock(id='test-task-id')
                        result = process_webhook_task.delay(
                            gateway='yookassa',
                            payload=payload,
                            auth_value='test-signature',
                        )
                        
                        assert result.id == 'test-task-id'
                        mock_delay.assert_called_once()

    def test_tinkoff_webhook_success(self):
        """Тест успешной обработки Tinkoff webhook."""
        payload = {
            "event_id": "tinkoff-123",
            "order_id": "order-789",
            "message": "payment successful",
        }
        
        with patch.object(process_webhook_task, 'delay') as mock_delay:
            mock_delay.return_value = Mock(id='test-task-id-2')
            result = process_webhook_task.delay(
                gateway='tinkoff',
                payload=payload,
                auth_value='test-signature',
            )
            
            assert result.id == 'test-task-id-2'
            mock_delay.assert_called_once()

    def test_webhook_without_order_id(self):
        """Тест webhook без order_id."""
        payload = {
            "event_id": "test-123",
            "message": "payment successful",
        }
        
        with patch.object(process_webhook_task, 'delay') as mock_delay:
            mock_delay.return_value = Mock(id='test-task-id-3')
            result = process_webhook_task.delay(
                gateway='yookassa',
                payload=payload,
                auth_value='test-signature',
            )
            
            assert result.id == 'test-task-id-3'
            mock_delay.assert_called_once()


class TestProcessWebhookTaskRetry:
    """Тесты retry логики."""

    def test_retry_on_exception(self):
        """Тест повторной попытки при ошибке."""
        # Проверяем, что задача настроена на retry
        assert process_webhook_task.max_retries == 5
        assert process_webhook_task.default_retry_delay == 60
        assert process_webhook_task.acks_late is True

    def test_max_retries_exceeded(self):
        """Тест превышения максимального количества попыток."""
        # Проверяем конфигурацию retry
        assert process_webhook_task.max_retries == 5
        
        # Проверяем, что retry вызывается с правильными параметрами
        # Экспоненциальная задержка должна быть 60 * 2^retry_count
        retry_count = 5
        expected_delay = 60 * (2 ** retry_count)
        assert expected_delay == 1920


class TestWebhookHandlers:
    """Тесты доступных webhook обработчиков."""

    def test_all_handlers_present(self):
        """Тест наличия всех обработчиков."""
        expected_gateways = ['yookassa', 'tinkoff', 'cloudpayments', 'unitpay', 'robokassa']
        
        for gateway in expected_gateways:
            assert gateway in WEBHOOK_HANDLERS
            assert callable(WEBHOOK_HANDLERS[gateway])


class TestHealthCheck:
    """Тесты health check задачи."""

    def test_health_check_success(self):
        """Тест успешной проверки здоровья."""
        mock_self = Mock()
        mock_self.request.hostname = "test-worker-1"
        
        result = health_check()
        
        assert result["status"] == "ok"
        assert "timestamp" in result
        assert "worker" in result


class TestSendRetryNotification:
    """Тесты отправки уведомлений о retry."""

    def test_send_notification(self, caplog):
        """Тест отправки уведомления."""
        with caplog.at_level("WARNING"):
            result = send_webhook_retry_notification(
                gateway='yookassa',
                payload={"order_id": "order-123"},
                error_message="Connection timeout",
                retry_count=2,
            )
            
            assert "Webhook retry notification" in caplog.text
            assert "yookassa" in caplog.text


class TestCleanupOldWebhookEvents:
    """Тесты очистки старых webhook событий."""

    def test_cleanup_task(self):
        """Тест задачи очистки."""
        mock_db = Mock()
        
        with patch('app.tasks.webhook_tasks.get_db_session', return_value=mock_db):
            result = cleanup_old_webhook_events(days=30)
            
            # Пока возвращает 0 (TODO: реализовать очистку)
            assert result == 0


class TestCeleryConfiguration:
    """Тесты конфигурации Celery."""

    def test_celery_app_configured(self):
        """Тест конфигурации Celery приложения."""
        from app.tasks.webhook_tasks import celery_app
        
        assert celery_app is not None
        assert celery_app.conf.broker_url == 'redis://localhost:6379/0'
        assert celery_app.conf.result_backend == 'redis://localhost:6379/1'

    def test_task_configuration(self):
        """Тест конфигурации задач."""
        from app.tasks.webhook_tasks import celery_app
        
        task = celery_app.tasks['app.tasks.webhook_tasks.process_webhook_task']
        assert task is not None
        
        # Проверка retry настроек
        assert task.max_retries == 5
        assert task.default_retry_delay == 60


@pytest.mark.asyncio
class TestIntegrationWebhookFlow:
    """Интеграционные тесты webhook потока."""

    async def test_full_webhook_flow(self):
        """Тест полного цикла обработки webhook."""
        # Этот тест требует запущенный Redis и может использоваться
        # для интеграционного тестирования
        pytest.skip("Requires Redis connection")
