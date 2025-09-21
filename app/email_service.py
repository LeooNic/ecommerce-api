"""
Email notification service for the application.
This implementation provides a simulated email service that can be easily
switched to real email providers in production.
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
from jinja2 import Template
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmailMessage:
    """
    Email message data structure.
    """
    to: str
    subject: str
    body: str
    html_body: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None


class EmailTemplates:
    """
    Email templates for different types of notifications.
    """

    WELCOME_TEMPLATE = """
    <html>
    <body>
        <h2>Welcome to {{ app_name }}!</h2>
        <p>Hello {{ user_name }},</p>
        <p>Thank you for registering with us. Your account has been successfully created.</p>
        <p>Account details:</p>
        <ul>
            <li>Email: {{ user_email }}</li>
            <li>Registration Date: {{ registration_date }}</li>
        </ul>
        <p>You can now start exploring our products and services.</p>
        <p>Best regards,<br>{{ app_name }} Team</p>
    </body>
    </html>
    """

    ORDER_CONFIRMATION_TEMPLATE = """
    <html>
    <body>
        <h2>Order Confirmation - {{ app_name }}</h2>
        <p>Hello {{ user_name }},</p>
        <p>Thank you for your order! We have received your order and it's being processed.</p>

        <h3>Order Details:</h3>
        <ul>
            <li>Order ID: {{ order_id }}</li>
            <li>Order Date: {{ order_date }}</li>
            <li>Total Amount: ${{ total_amount }}</li>
            <li>Status: {{ order_status }}</li>
        </ul>

        <h3>Ordered Items:</h3>
        <ul>
        {% for item in items %}
            <li>{{ item.product_name }} - Quantity: {{ item.quantity }} - Price: ${{ item.price }}</li>
        {% endfor %}
        </ul>

        <p>We will notify you when your order is shipped.</p>
        <p>Thank you for choosing {{ app_name }}!</p>
        <p>Best regards,<br>{{ app_name }} Team</p>
    </body>
    </html>
    """

    PASSWORD_RESET_TEMPLATE = """
    <html>
    <body>
        <h2>Password Reset Request - {{ app_name }}</h2>
        <p>Hello {{ user_name }},</p>
        <p>We received a request to reset your password. If you made this request, please use the information below:</p>

        <p><strong>Reset Token:</strong> {{ reset_token }}</p>
        <p><strong>This token expires at:</strong> {{ expiry_time }}</p>

        <p>If you did not request a password reset, please ignore this email and your password will remain unchanged.</p>
        <p>For security reasons, this link will expire in 1 hour.</p>

        <p>Best regards,<br>{{ app_name }} Team</p>
    </body>
    </html>
    """

    ADMIN_NOTIFICATION_TEMPLATE = """
    <html>
    <body>
        <h2>Admin Notification - {{ app_name }}</h2>
        <p>Hello Admin,</p>
        <p>{{ notification_type }} notification:</p>

        <h3>Details:</h3>
        <ul>
        {% for key, value in details.items() %}
            <li>{{ key }}: {{ value }}</li>
        {% endfor %}
        </ul>

        <p>Timestamp: {{ timestamp }}</p>
        <p>Please take appropriate action if required.</p>

        <p>{{ app_name }} System</p>
    </body>
    </html>
    """


class SimulatedEmailService:
    """
    Simulated email service for development and testing.
    In production, this would be replaced with real email service integration.
    """

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []
        self.email_log_file = "logs/emails.json"

    async def send_email(self, message: EmailMessage) -> bool:
        """
        Simulate sending an email by logging it.

        Args:
            message: Email message to send

        Returns:
            True if email was "sent" successfully
        """
        try:
            email_data = {
                "timestamp": datetime.now().isoformat(),
                "to": message.to,
                "from": message.from_email or f"noreply@{settings.app_name.lower().replace(' ', '')}.com",
                "subject": message.subject,
                "body": message.body,
                "html_body": message.html_body,
                "reply_to": message.reply_to
            }

            # Store in memory
            self.sent_emails.append(email_data)

            # Log to file
            await self._log_email_to_file(email_data)

            logger.info(
                "email_sent_simulated",
                to=message.to,
                subject=message.subject,
                timestamp=email_data["timestamp"]
            )

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False

    async def _log_email_to_file(self, email_data: Dict[str, Any]) -> None:
        """
        Log email data to file for inspection.

        Args:
            email_data: Email data to log
        """
        try:
            import os
            os.makedirs("logs", exist_ok=True)

            # Read existing emails
            existing_emails = []
            try:
                with open(self.email_log_file, 'r', encoding='utf-8') as f:
                    existing_emails = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            # Add new email
            existing_emails.append(email_data)

            # Keep only last 100 emails to prevent file from growing too large
            if len(existing_emails) > 100:
                existing_emails = existing_emails[-100:]

            # Write back to file
            with open(self.email_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_emails, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to log email to file: {e}")

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """
        Get list of sent emails for inspection.

        Returns:
            List of sent email data
        """
        return self.sent_emails.copy()

    def clear_sent_emails(self) -> None:
        """Clear the sent emails list."""
        self.sent_emails.clear()


class EmailNotificationService:
    """
    High-level email notification service.
    """

    def __init__(self, email_service: SimulatedEmailService = None):
        self.email_service = email_service or SimulatedEmailService()

    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """
        Send welcome email to new user.

        Args:
            user_email: User's email address
            user_name: User's name

        Returns:
            True if email was sent successfully
        """
        template = Template(EmailTemplates.WELCOME_TEMPLATE)
        html_body = template.render(
            app_name=settings.app_name,
            user_name=user_name,
            user_email=user_email,
            registration_date=datetime.now().strftime("%B %d, %Y")
        )

        message = EmailMessage(
            to=user_email,
            subject=f"Welcome to {settings.app_name}!",
            body=f"Welcome {user_name}! Thank you for registering with {settings.app_name}.",
            html_body=html_body
        )

        return await self.email_service.send_email(message)

    async def send_order_confirmation(self, user_email: str, user_name: str, order_data: Dict[str, Any]) -> bool:
        """
        Send order confirmation email.

        Args:
            user_email: User's email address
            user_name: User's name
            order_data: Order information

        Returns:
            True if email was sent successfully
        """
        template = Template(EmailTemplates.ORDER_CONFIRMATION_TEMPLATE)
        html_body = template.render(
            app_name=settings.app_name,
            user_name=user_name,
            order_id=order_data.get("id"),
            order_date=order_data.get("created_at", datetime.now()).strftime("%B %d, %Y"),
            total_amount=order_data.get("total_amount", 0),
            order_status=order_data.get("status", "Processing"),
            items=order_data.get("items", [])
        )

        message = EmailMessage(
            to=user_email,
            subject=f"Order Confirmation #{order_data.get('id')} - {settings.app_name}",
            body=f"Thank you for your order #{order_data.get('id')}!",
            html_body=html_body
        )

        return await self.email_service.send_email(message)

    async def send_password_reset_email(self, user_email: str, user_name: str, reset_token: str) -> bool:
        """
        Send password reset email.

        Args:
            user_email: User's email address
            user_name: User's name
            reset_token: Password reset token

        Returns:
            True if email was sent successfully
        """
        from datetime import timedelta
        expiry_time = (datetime.now() + timedelta(hours=1)).strftime("%B %d, %Y at %I:%M %p")

        template = Template(EmailTemplates.PASSWORD_RESET_TEMPLATE)
        html_body = template.render(
            app_name=settings.app_name,
            user_name=user_name,
            reset_token=reset_token,
            expiry_time=expiry_time
        )

        message = EmailMessage(
            to=user_email,
            subject=f"Password Reset Request - {settings.app_name}",
            body=f"Password reset requested for {user_email}. Token: {reset_token}",
            html_body=html_body
        )

        return await self.email_service.send_email(message)

    async def send_admin_notification(self, notification_type: str, details: Dict[str, Any]) -> bool:
        """
        Send notification to administrators.

        Args:
            notification_type: Type of notification
            details: Notification details

        Returns:
            True if email was sent successfully
        """
        admin_email = getattr(settings, 'admin_email', 'admin@example.com')

        template = Template(EmailTemplates.ADMIN_NOTIFICATION_TEMPLATE)
        html_body = template.render(
            app_name=settings.app_name,
            notification_type=notification_type,
            details=details,
            timestamp=datetime.now().strftime("%B %d, %Y at %I:%M %p")
        )

        message = EmailMessage(
            to=admin_email,
            subject=f"Admin Notification: {notification_type} - {settings.app_name}",
            body=f"Admin notification: {notification_type}",
            html_body=html_body
        )

        return await self.email_service.send_email(message)


# Global email service instance
email_service = EmailNotificationService()