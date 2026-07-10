"""Factory Method — gateways Cielo e Rede."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import time
import random


class GatewayType(str, Enum):
    CIELO = "cielo"
    REDE = "rede"


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    message: str
    latency_ms: float


class PaymentGateway(ABC):
    @abstractmethod
    def process(self, amount: float, card_token: str) -> PaymentResult:
        pass


class CieloGateway(PaymentGateway):
    def process(self, amount: float, card_token: str) -> PaymentResult:
        start = time.perf_counter()
        # simula latência do gateway
        time.sleep(random.uniform(0.1, 0.5))
        latency = (time.perf_counter() - start) * 1000
        return PaymentResult(
            success=True,
            transaction_id=f"CIELO-{int(time.time() * 1000)}",
            message="Pagamento autorizado via Cielo",
            latency_ms=latency,
        )


class RedeGateway(PaymentGateway):
    def process(self, amount: float, card_token: str) -> PaymentResult:
        start = time.perf_counter()
        time.sleep(random.uniform(0.1, 0.5))
        latency = (time.perf_counter() - start) * 1000
        return PaymentResult(
            success=True,
            transaction_id=f"REDE-{int(time.time() * 1000)}",
            message="Pagamento autorizado via Rede",
            latency_ms=latency,
        )


class SlowGateway(PaymentGateway):
    """Usado em testes para simular timeout > 3s (RN01)."""

    def process(self, amount: float, card_token: str) -> PaymentResult:
        time.sleep(4)
        return PaymentResult(
            success=False,
            transaction_id="",
            message="Timeout simulado",
            latency_ms=4000,
        )


class PaymentGatewayFactory:
    @staticmethod
    def create(gateway_type: GatewayType) -> PaymentGateway:
        if gateway_type == GatewayType.CIELO:
            return CieloGateway()
        if gateway_type == GatewayType.REDE:
            return RedeGateway()
        raise ValueError(f"Gateway desconhecido: {gateway_type}")
