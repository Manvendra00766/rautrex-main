import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_data import CompanyTickerMapping
from services.ticker_resolver import ticker_resolver_service

@pytest.mark.asyncio
async def test_ticker_resolver_normalization():
    """Verify that user search queries are semantically normalized and cleaned."""
    assert ticker_resolver_service.normalize_query("  TATA   MOTORS  ") == "tata motors"
    assert ticker_resolver_service.normalize_query("Google\n") == "google"
    assert ticker_resolver_service.normalize_query("CRUDE   OIL\t") == "crude oil"
    assert ticker_resolver_service.normalize_query("") == ""
    assert ticker_resolver_service.normalize_query(None) == ""

@pytest.mark.asyncio
async def test_ticker_resolver_cache_hit():
    """Verify that cached mappings resolve instantly directly from the database without network calls."""
    # Create mock session and database mapping return
    mock_db = AsyncMock(spec=AsyncSession)
    mock_mapping = CompanyTickerMapping(
        user_query="tata motors",
        resolved_ticker="TATAMOTORS.NS",
        confidence_score=1.0
    )
    
    # Mock database select query execution
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_mapping
    mock_db.execute.return_value = mock_result
    
    # Call resolver and mock the network client to ensure it is NEVER called
    with patch("httpx.AsyncClient.get") as mock_http_get:
        ticker = await ticker_resolver_service.resolve("Tata Motors", mock_db)
        
        assert ticker == "TATAMOTORS.NS"
        mock_http_get.assert_not_called()
        mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_ticker_resolver_cache_miss_and_fetch():
    """Verify Yahoo Search is queried on cache miss, caches results dynamically, and returns the top ticker."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Setup cache miss (db returns None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock Yahoo Finance API successful response payload
    yahoo_payload = {
        "quotes": [
            {"symbol": "GOOGL", "shortname": "Alphabet Inc."},
            {"symbol": "GOOG", "shortname": "Alphabet Inc. Cl C"}
        ]
    }
    
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = yahoo_payload
    
    # Mock HTTP client query execution
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        ticker = await ticker_resolver_service.resolve("Google", mock_db)
        
        assert ticker == "GOOGL"
        
        # Verify URL encoding and API request headers are mapped correctly
        mock_get.assert_called_once()
        called_args, called_kwargs = mock_get.call_args
        assert "v1/finance/search" in called_args[0]
        assert "q=google" in called_args[0]
        assert "User-Agent" in called_kwargs["headers"]
        
        # Verify result was saved/cached in local database
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, CompanyTickerMapping)
        assert added_obj.user_query == "google"
        assert added_obj.resolved_ticker == "GOOGL"
        mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_ticker_resolver_yahoo_api_error_handling():
    """Verify that resolver handles external network failures gracefully and safely fails back."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Cache miss
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Mock Yahoo API returning an HTTP 500 error
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        ticker = await ticker_resolver_service.resolve("ErrorCompany", mock_db)
        
        assert ticker is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

@pytest.mark.asyncio
async def test_ticker_resolver_network_timeout():
    """Verify that timeout/transport network exceptions are swallowed safely without blocking."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Cache miss
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    # Trigger timeout exception
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Connection timed out")) as mock_get:
        ticker = await ticker_resolver_service.resolve("TimeoutCompany", mock_db)
        
        assert ticker is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
