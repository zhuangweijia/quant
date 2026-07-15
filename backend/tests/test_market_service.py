import builtins

from app.services import market_service


def test_get_provider_caches_mock_when_discoverable_akshare_cannot_import(monkeypatch):
    monkeypatch.setattr(market_service, "_providers", {})
    monkeypatch.setattr(market_service, "find_spec", lambda name: object())
    real_import = builtins.__import__

    def import_without_akshare(name, *args, **kwargs):
        if name == "akshare":
            raise ImportError("missing transitive dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_akshare)

    provider = market_service.get_provider("a_stock")

    assert isinstance(provider, market_service.MockDataProvider)
    assert market_service.get_provider("a_stock") is provider
