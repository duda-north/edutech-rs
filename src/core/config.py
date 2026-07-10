"""Singleton — centraliza config da aplicação."""
from __future__ import annotations

import os
from threading import Lock
from typing import Optional


class ConfigManager:
    _instance: Optional[ConfigManager] = None
    _lock = Lock()

    def __new__(cls) -> ConfigManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.payment_timeout_seconds = float(os.getenv("PAYMENT_TIMEOUT_SECONDS", "3"))
        self.audit_signature = os.getenv(
            "AUDIT_SIGNATURE", "COREDE-CENTRO-SUL-SECURE-2026"
        )
        self.min_test_coverage = float(os.getenv("MIN_TEST_COVERAGE", "80"))
        self._initialized = True

    @classmethod
    def reset_for_tests(cls) -> None:
        """Só uso nos testes."""
        with cls._lock:
            cls._instance = None
