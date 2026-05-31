import pytest
from services.market_data_service import market_data_service
from services.adapters.alpaca_adapter import AlpacaAdapter
from services.adapters.upstox_adapter import UpstoxAdapter
from services.adapters.oanda_adapter import OandaAdapter

@pytest.mark.asyncio
async def test_intelligent_routing():
    """Verify that tickers are routed to the correct adapters based on naming rules."""
    # US Stock should route to Alpaca
    adapter_us = market_data_service._get_adapter("AAPL")
    assert isinstance(adapter_us, AlpacaAdapter)

    # Indian Stock should route to Upstox
    adapter_in = market_data_service._get_adapter("RELIANCE.NS")
    assert isinstance(adapter_in, UpstoxAdapter)
    
    adapter_in_bse = market_data_service._get_adapter("TCS.BO")
    assert isinstance(adapter_in_bse, UpstoxAdapter)

    # Commodities should route to OANDA
    adapter_comm = market_data_service._get_adapter("GC=F")
    assert isinstance(adapter_comm, OandaAdapter)

    adapter_comm_oil = market_data_service._get_adapter("CL=F")
    assert isinstance(adapter_comm_oil, OandaAdapter)

@pytest.mark.asyncio
async def test_unified_response_structure_us():
    """Verify standard US equities price fetching returns the unified JSON schema."""
    data = await market_data_service.fetch_price("MSFT")
    
    assert "ticker" in data
    assert data["ticker"] == "MSFT"
    assert "price" in data
    assert isinstance(data["price"], float)
    assert "currency" in data
    assert data["currency"] == "USD"
    assert "source" in data
    assert "Alpaca" in data["source"]
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_unified_response_structure_indian():
    """Verify standard Indian equities price fetching returns the unified JSON schema."""
    # We use a highly liquid stock for testing like INFy
    data = await market_data_service.fetch_price("INFY.NS")
    
    assert "ticker" in data
    assert data["ticker"] == "INFY.NS"
    assert "price" in data
    assert isinstance(data["price"], float)
    assert "currency" in data
    assert data["currency"] == "INR"
    assert "source" in data
    assert "Upstox" in data["source"]
    assert "timestamp" in data

@pytest.mark.asyncio
async def test_unified_response_structure_commodity():
    """Verify commodity price fetching returns the unified JSON schema."""
    data = await market_data_service.fetch_price("GC=F")
    
    assert "ticker" in data
    assert data["ticker"] == "GC=F"
    assert "price" in data
    assert isinstance(data["price"], float)
    assert "currency" in data
    assert data["currency"] == "USD"
    assert "source" in data
    assert "OANDA" in data["source"]
    assert "timestamp" in data
