import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock
from services.screener_service import ScreenerService
from schemas.screener_schema import ScreenerFilter, ScreenerRequest, ScreenerResult

@pytest.fixture
def screener_service():
    return ScreenerService()

@pytest.fixture
def mock_redis():
    with patch("services.screener_service.redis_client", new_callable=AsyncMock) as mocked:
        yield mocked

@patch("services.screener_service.yf.Ticker")
@pytest.mark.asyncio
async def test_fetch_stock_metrics_success(mock_ticker, screener_service, mock_redis):
    """fetch_stock_metrics: yfinance returns valid dict → all fields mapped correctly"""
    mock_redis.get.return_value = None
    
    mock_stock = MagicMock()
    mock_stock.info = {
        "longName": "Reliance Industries Limited",
        "trailingPE": 25.5,
        "priceToBook": 2.1,
        "earningsGrowth": 0.15,
        "revenueGrowth": 0.1,
        "marketCap": 17000000000000,
        "currentPrice": 2500.0,
        "fiftyTwoWeekHigh": 2800.0
    }
    mock_ticker.return_value = mock_stock
    
    # Mock RSI calculation to avoid network call
    with patch.object(ScreenerService, 'calculate_rsi', return_value=45.0):
        result = await screener_service.fetch_stock_metrics("RELIANCE.NS")
    
    assert result.ticker == "RELIANCE.NS"
    assert result.company_name == "Reliance Industries Limited"
    assert result.pe_ratio == 25.5
    assert result.pb_ratio == 2.1
    assert result.eps_growth_yoy == 0.15
    assert result.revenue_growth_yoy == 0.1
    assert result.market_cap_cr == 1700000.0
    assert result.current_price == 2500.0
    assert result.week_52_from_high_pct == pytest.approx(((2500 - 2800) / 2800) * 100)
    assert result.rsi_14 == 45.0

@patch("services.screener_service.yf.Ticker")
@pytest.mark.asyncio
async def test_fetch_stock_metrics_failure(mock_ticker, screener_service, mock_redis):
    """fetch_stock_metrics: yfinance raises exception → returns ScreenerResult with all None"""
    mock_redis.get.return_value = None
    mock_ticker.side_effect = Exception("API Error")
    
    result = await screener_service.fetch_stock_metrics("RELIANCE.NS")
    
    assert result.ticker == "RELIANCE.NS"
    assert result.pe_ratio is None
    assert result.market_cap_cr is None

@pytest.mark.asyncio
async def test_fetch_stock_metrics_cache_hit(screener_service, mock_redis):
    """fetch_stock_metrics: Redis cache hit → yfinance NOT called"""
    cached_result = ScreenerResult(ticker="RELIANCE.NS", company_name="Reliance", pe_ratio=20.0)
    mock_redis.get.return_value = cached_result.model_dump_json()
    
    with patch("services.screener_service.yf.Ticker") as mock_ticker:
        result = await screener_service.fetch_stock_metrics("RELIANCE.NS")
        mock_ticker.assert_not_called()
    
    assert result.ticker == "RELIANCE.NS"
    assert result.pe_ratio == 20.0

@patch("services.screener_service.yf.download")
def test_calculate_rsi_correctness(mock_download, screener_service):
    """RSI calculation: known price series → correct RSI value"""
    # Create a simple price series where RSI is predictable
    # 15 days of data (14 diffs)
    prices = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122, 124, 126, 128]
    df = pd.DataFrame({"Close": prices})
    mock_download.return_value = df
    
    rsi = screener_service.calculate_rsi("RELIANCE.NS")
    # All gains, 0 losses -> RSI should be 100
    assert rsi == 100.0

    # Test with some losses
    # Diffs: [2, -2, 2, -2, ...]
    prices = [100, 102, 100, 102, 100, 102, 100, 102, 100, 102, 100, 102, 100, 102, 100]
    df = pd.DataFrame({"Close": prices})
    mock_download.return_value = df
    
    # avg_gain = 2, avg_loss = 2 (over 14 periods)
    # RS = 1, RSI = 100 - (100 / 2) = 50
    rsi = screener_service.calculate_rsi("RELIANCE.NS")
    assert rsi == pytest.approx(50.0)

def test_apply_filter_gt_success(screener_service):
    """apply_filter: gt operator, value present → correct bool"""
    result = ScreenerResult(ticker="REL", company_name="Rel", pe_ratio=25.0)
    filt = ScreenerFilter(metric="pe_ratio", operator="gt", value=20.0)
    assert screener_service.apply_filter(result, filt) is True

def test_apply_filter_metric_none(screener_service):
    """apply_filter: metric is None → returns False"""
    result = ScreenerResult(ticker="REL", company_name="Rel", pe_ratio=None)
    filt = ScreenerFilter(metric="pe_ratio", operator="gt", value=20.0)
    assert screener_service.apply_filter(result, filt) is False

@pytest.mark.parametrize("operator,val,expected", [
    ("lt", 30.0, True),
    ("lt", 20.0, False),
    ("gt", 20.0, True),
    ("gt", 30.0, False),
    ("lte", 25.0, True),
    ("lte", 24.0, False),
    ("gte", 25.0, True),
    ("gte", 26.0, False),
])
def test_apply_filter_operators(screener_service, operator, val, expected):
    """apply_filter: all 4 operators tested"""
    result = ScreenerResult(ticker="REL", company_name="Rel", pe_ratio=25.0)
    filt = ScreenerFilter(metric="pe_ratio", operator=operator, value=val)
    assert screener_service.apply_filter(result, filt) == expected

@patch.object(ScreenerService, 'fetch_stock_metrics')
@pytest.mark.asyncio
async def test_run_screener_filtering(mock_fetch, screener_service):
    """run_screener: 2 stocks pass filters, 1 fails → returns 2 results"""
    # Mock NIFTY50_TICKERS to only have 3 for this test
    with patch("services.screener_service.NIFTY50_TICKERS", ["S1.NS", "S2.NS", "S3.NS"]):
        mock_fetch.side_effect = [
            ScreenerResult(ticker="S1.NS", company_name="S1", pe_ratio=10.0, market_cap_cr=100),
            ScreenerResult(ticker="S2.NS", company_name="S2", pe_ratio=30.0, market_cap_cr=200),
            ScreenerResult(ticker="S3.NS", company_name="S3", pe_ratio=15.0, market_cap_cr=300),
        ]
        
        request = ScreenerRequest(
            filters=[ScreenerFilter(metric="pe_ratio", operator="lt", value=20.0)],
            universe="nifty50",
            limit=10
        )
        
        results = await screener_service.run_screener(request)
        assert len(results) == 2
        assert results[0].ticker == "S3.NS"  # Higher market cap first
        assert results[1].ticker == "S1.NS"

@patch.object(ScreenerService, 'fetch_stock_metrics')
@pytest.mark.asyncio
async def test_run_screener_empty_filters(mock_fetch, screener_service):
    """run_screener: empty filters → returns all stocks up to limit"""
    with patch("services.screener_service.NIFTY50_TICKERS", ["S1.NS", "S2.NS"]):
        mock_fetch.side_effect = [
            ScreenerResult(ticker="S1.NS", company_name="S1", market_cap_cr=100),
            ScreenerResult(ticker="S2.NS", company_name="S2", market_cap_cr=200),
        ]
        
        request = ScreenerRequest(filters=[], universe="nifty50", limit=10)
        results = await screener_service.run_screener(request)
        assert len(results) == 2

@patch.object(ScreenerService, 'fetch_stock_metrics')
@pytest.mark.asyncio
async def test_run_screener_limit(mock_fetch, screener_service):
    """run_screener: limit=2 → returns max 2 results"""
    with patch("services.screener_service.NIFTY50_TICKERS", ["S1.NS", "S2.NS", "S3.NS"]):
        mock_fetch.side_effect = [
            ScreenerResult(ticker="S1.NS", company_name="S1", market_cap_cr=100),
            ScreenerResult(ticker="S2.NS", company_name="S2", market_cap_cr=200),
            ScreenerResult(ticker="S3.NS", company_name="S3", market_cap_cr=300),
        ]
        
        request = ScreenerRequest(filters=[], universe="nifty50", limit=2)
        results = await screener_service.run_screener(request)
        assert len(results) == 2
