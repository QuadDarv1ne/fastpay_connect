"""Сервис email уведомлений."""

import logging
from typing import Optional, List
from app.settings import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Сервис отправки email уведомлений."""

    def __init__(self):
        self.enabled = settings.mail_enabled
        self.smtp_server = settings.mail_server
        self.smtp_port = settings.mail_port
        self.username = settings.mail_username
        self.password = settings.mail_password
        self.from_email = settings.mail_from_email

    async def send_payment_notification(
        self,
        to_email: str,
        payment_id: str,
        amount: float,
        status: str,
        description: str,
    ) -> bool:
        """Отправить уведомление о платеже."""
        if not self.enabled:
            logger.debug("Email notifications disabled")
            return False

        if not all([self.smtp_server, self.username, self.password, self.from_email]):
            logger.warning("Email configuration incomplete")
            return False

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = f"Платёж {payment_id} - {status}"

            body = f"""
            Статус платежа: {status}
            ID платежа: {payment_id}
            Сумма: {amount} RUB
            Описание: {description}
            """
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_email} for payment {payment_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_bulk_notification(
        self,
        emails: List[str],
        subject: str,
        body: str,
    ) -> int:
        """Отправить массовое уведомление."""
        if not self.enabled:
            return 0

        sent_count = 0
        for email in emails:
            try:
                import smtplib
                from email.mime.text import MIMEText

                msg = MIMEText(body)
                msg["From"] = self.from_email
                msg["To"] = email
                msg["Subject"] = subject

                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(msg)

                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to {email}: {e}")

        return sent_count


email_service = EmailService()
