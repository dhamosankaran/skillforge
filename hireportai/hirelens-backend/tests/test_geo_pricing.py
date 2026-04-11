"""Tests for geo-based pricing service."""
from unittest.mock import MagicMock, patch
import json

import pytest

from app.services.geo_pricing_service import get_pricing


@pytest.fixture(autouse=True)
def _mock_settings(monkeypatch):
    """Provide minimal settings for all tests."""
    mock_settings = MagicMock()
    mock_settings.redis_url = ""
    mock_settings.stripe_pro_price_id = "price_usd_test"
    mock_settings.stripe_pro_price_id_inr = "price_inr_test"
    monkeypatch.setattr(
        "app.services.geo_pricing_service.get_settings",
        lambda: mock_settings,
    )
    return mock_settings


class TestIndiaPricing:
    """Indian IPs should get INR pricing."""

    def test_india_ip_returns_inr_pricing(self, _mock_settings):
        with patch("app.services.geo_pricing_service._lookup_country", return_value="IN"):
            result = get_pricing("103.21.244.0")

        assert result["currency"] == "inr"
        assert result["price"] == 999
        assert result["price_display"] == "\u20b9999/mo"
        assert result["stripe_price_id"] == "price_inr_test"


class TestUSPricing:
    """US (and all non-IN) IPs should get USD pricing."""

    def test_us_ip_returns_usd_pricing(self, _mock_settings):
        with patch("app.services.geo_pricing_service._lookup_country", return_value="US"):
            result = get_pricing("8.8.8.8")

        assert result["currency"] == "usd"
        assert result["price"] == 49
        assert result["price_display"] == "$49/mo"
        assert result["stripe_price_id"] == "price_usd_test"


class TestGeoAPIFailure:
    """When the geolocation API fails, default to USD."""

    def test_api_failure_defaults_to_usd(self, _mock_settings):
        with patch("app.services.geo_pricing_service._lookup_country", return_value=None):
            result = get_pricing("0.0.0.0")

        assert result["currency"] == "usd"
        assert result["price"] == 49


class TestRedisCache:
    """Verify that results are cached in Redis."""

    def test_pricing_cached_in_redis(self, _mock_settings):
        _mock_settings.redis_url = "redis://localhost:6379"

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None  # Cache miss on first call

        with (
            patch("app.services.geo_pricing_service._get_redis", return_value=mock_redis),
            patch("app.services.geo_pricing_service._lookup_country", return_value="IN") as mock_lookup,
        ):
            result1 = get_pricing("103.21.244.0")

            # Verify setex was called to cache
            mock_redis.setex.assert_called_once()
            cached_key = mock_redis.setex.call_args[0][0]
            cached_ttl = mock_redis.setex.call_args[0][1]
            assert cached_key == "geo_pricing:103.21.244.0"
            assert cached_ttl == 86_400

            # Now simulate cache hit on second call
            mock_redis.get.return_value = json.dumps(result1)
            mock_lookup.reset_mock()

            result2 = get_pricing("103.21.244.0")

            # Lookup should NOT have been called again
            mock_lookup.assert_not_called()
            assert result2 == result1
