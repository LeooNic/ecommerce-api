"""
Payment service for processing simulated payments.
"""

import time
import uuid
from decimal import Decimal
from random import random
from typing import Any, Dict

from app.models.order import PaymentStatus
from app.schemas.order import PaymentRequest, PaymentResponse


class PaymentService:
    """
    Simulated payment service for processing payments.
    """

    # Simulamos diferentes métodos de pago y sus tasas de éxito
    PAYMENT_METHODS = {
        "credit_card": {"success_rate": 0.95, "processing_time": 2.0},
        "debit_card": {"success_rate": 0.92, "processing_time": 1.5},
        "paypal": {"success_rate": 0.98, "processing_time": 3.0},
        "bank_transfer": {"success_rate": 0.99, "processing_time": 5.0},
        "crypto": {"success_rate": 0.85, "processing_time": 10.0},
    }

    def __init__(self):
        """
        Initialize payment service.
        """
        pass

    def process_payment(self, payment_request: PaymentRequest) -> PaymentResponse:
        """
        Process a payment request (simulated).

        Args:
            payment_request: Payment request details

        Returns:
            PaymentResponse: Payment processing result
        """
        # Generar ID de transacción único
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        # Validar método de pago
        if payment_request.payment_method not in self.PAYMENT_METHODS:
            return PaymentResponse(
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                message="Unsupported payment method",
            )

        # Simular tiempo de procesamiento
        method_config = self.PAYMENT_METHODS[payment_request.payment_method]
        processing_time = method_config["processing_time"]
        time.sleep(min(processing_time / 10, 0.5))  # Reducido para pruebas

        # Simular éxito/fallo basado en la tasa de éxito
        success_rate = method_config["success_rate"]
        is_successful = random() < success_rate

        if is_successful:
            return PaymentResponse(
                transaction_id=transaction_id,
                status=PaymentStatus.COMPLETED,
                amount=payment_request.amount,
                message=f"Payment processed successfully via {payment_request.payment_method}",
            )
        else:
            # Simulamos diferentes tipos de fallos
            failure_reasons = [
                "Insufficient funds",
                "Card declined",
                "Network timeout",
                "Invalid card details",
                "Payment limit exceeded",
            ]
            failure_reason = failure_reasons[int(random() * len(failure_reasons))]

            return PaymentResponse(
                transaction_id=transaction_id,
                status=PaymentStatus.FAILED,
                amount=payment_request.amount,
                message=f"Payment failed: {failure_reason}",
            )

    def validate_payment_method(self, method: str) -> bool:
        """
        Validate if payment method is supported.

        Args:
            method: Payment method to validate

        Returns:
            bool: True if method is supported
        """
        return method in self.PAYMENT_METHODS

    def get_supported_methods(self) -> Dict[str, Any]:
        """
        Get list of supported payment methods.

        Returns:
            Dict[str, Any]: Supported payment methods with details
        """
        return {
            method: {
                "name": method.replace("_", " ").title(),
                "success_rate": config["success_rate"],
                "avg_processing_time": f"{config['processing_time']}s",
            }
            for method, config in self.PAYMENT_METHODS.items()
        }

    def refund_payment(self, transaction_id: str, amount: Decimal) -> PaymentResponse:
        """
        Process a refund (simulated).

        Args:
            transaction_id: Original transaction ID
            amount: Amount to refund

        Returns:
            PaymentResponse: Refund processing result
        """
        # Generar ID de refund
        refund_id = f"ref_{uuid.uuid4().hex[:12]}"

        # Simular procesamiento de refund (95% de éxito)
        is_successful = random() < 0.95

        if is_successful:
            return PaymentResponse(
                transaction_id=refund_id,
                status=PaymentStatus.REFUNDED,
                amount=amount,
                message=f"Refund processed successfully for transaction {transaction_id}",
            )
        else:
            return PaymentResponse(
                transaction_id=refund_id,
                status=PaymentStatus.FAILED,
                amount=amount,
                message=f"Refund failed for transaction {transaction_id}",
            )
