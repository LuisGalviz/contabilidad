from __future__ import annotations

import pytest

from src.config import Settings
from src.infrastructure.accounting import factory
from src.infrastructure.accounting.internal_accounting_system import InternalAccountingSystem
from src.infrastructure.siigo.accounting_system import SiigoAccountingSystem
from src.infrastructure.siigo.client import SiigoHttpClient
from src.infrastructure.siigo.errors import SiigoConfigurationError
from src.infrastructure.siigo.mock_client import MockSiigoClient


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_secret_key": "x" * 32,
        "database_url": "sqlite+aiosqlite:///:memory:",
        "jwt_secret_key": "x" * 32,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _clear_client_caches():
    factory._shared_siigo_client.cache_clear()
    factory._shared_mock_client.cache_clear()
    yield
    factory._shared_siigo_client.cache_clear()
    factory._shared_mock_client.cache_clear()


class TestBuildAccountingSystem:
    def test_siigo_disabled_returns_internal(self, monkeypatch):
        monkeypatch.setattr(factory, "get_settings", lambda: _settings(siigo_enabled=False))
        system = factory.build_accounting_system(causation_repo=None)  # type: ignore[arg-type]
        assert isinstance(system, InternalAccountingSystem)

    def test_siigo_enabled_with_mock_returns_siigo_with_mock_client(self, monkeypatch):
        monkeypatch.setattr(
            factory, "get_settings", lambda: _settings(siigo_enabled=True, siigo_use_mock=True)
        )
        system = factory.build_accounting_system(causation_repo=None)  # type: ignore[arg-type]
        assert isinstance(system, SiigoAccountingSystem)
        assert isinstance(system._siigo, MockSiigoClient)

    def test_siigo_real_without_credentials_raises(self, monkeypatch):
        monkeypatch.setattr(
            factory, "get_settings", lambda: _settings(siigo_enabled=True, siigo_use_mock=False)
        )
        with pytest.raises(SiigoConfigurationError):
            factory.build_accounting_system(causation_repo=None)  # type: ignore[arg-type]

    def test_siigo_real_without_document_id_raises(self, monkeypatch):
        monkeypatch.setattr(
            factory,
            "get_settings",
            lambda: _settings(
                siigo_enabled=True,
                siigo_use_mock=False,
                siigo_username="api@empresa.com",
                siigo_access_key="key",
                siigo_journal_document_id=0,
            ),
        )
        with pytest.raises(SiigoConfigurationError):
            factory.build_accounting_system(causation_repo=None)  # type: ignore[arg-type]

    def test_siigo_real_fully_configured_returns_http_client(self, monkeypatch):
        monkeypatch.setattr(
            factory,
            "get_settings",
            lambda: _settings(
                siigo_enabled=True,
                siigo_use_mock=False,
                siigo_username="api@empresa.com",
                siigo_access_key="key",
                siigo_journal_document_id=27441,
            ),
        )
        system = factory.build_accounting_system(causation_repo=None)  # type: ignore[arg-type]
        assert isinstance(system, SiigoAccountingSystem)
        assert isinstance(system._siigo, SiigoHttpClient)
