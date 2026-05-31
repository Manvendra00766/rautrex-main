import pytest
from pydantic import ValidationError
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.paper_trading_schema import PlaceOrderRequest
from middleware.exception_handler import setup_exception_handlers

def test_place_order_validation_success():
    """Verify that a valid order request passes validation successfully."""
    req = PlaceOrderRequest(
        ticker="  AAPL  ",  # Spaces should be stripped
        side="BUY",
        quantity=10,
        order_type="LIMIT",
        limit_price=180.5
    )
    assert req.ticker == "AAPL"
    assert req.quantity == 10
    assert req.side == "BUY"
    assert req.limit_price == 180.5

def test_place_order_validation_casing_and_sanitization():
    """Verify that ticker casing is normalized and script tags/HTML injections are stripped."""
    # Test script injection
    req_script = PlaceOrderRequest(
        ticker="<script>alert('hack')</script>reliance.ns",
        side="SELL",
        quantity=5
    )
    assert req_script.ticker == "RELIANCE.NS"

    # Test HTML injection
    req_html = PlaceOrderRequest(
        ticker="<div>TCS.BO</div>",
        side="BUY",
        quantity=1
    )
    assert req_html.ticker == "TCS.BO"

def test_place_order_validation_failures():
    """Verify that invalid tickers, quantities, or prices raise Pydantic ValidationErrors."""
    # Invalid ticker character
    with pytest.raises(ValidationError) as exc_info:
        PlaceOrderRequest(ticker="AAPL$!", side="BUY", quantity=10)
    assert "ticker" in str(exc_info.value)

    # Quantity <= 0
    with pytest.raises(ValidationError) as exc_info:
        PlaceOrderRequest(ticker="AAPL", side="BUY", quantity=0)
    assert "quantity" in str(exc_info.value)

    # Price <= 0
    with pytest.raises(ValidationError) as exc_info:
        PlaceOrderRequest(ticker="AAPL", side="BUY", quantity=10, limit_price=-5.0)
    assert "limit_price" in str(exc_info.value)

@pytest.mark.asyncio
async def test_standardized_error_response_format():
    """Verify that validation failures are caught by the handler and return standard JSON details."""
    # Mock FastAPI app and setup our exception handlers
    from fastapi import FastAPI
    app = FastAPI()
    setup_exception_handlers(app)

    # Find the registered RequestValidationError exception handler
    handler = app.exception_handlers[RequestValidationError]

    # Mock a Pydantic validation error info
    errors = [
        {
            "loc": ["body", "quantity"],
            "msg": "Input should be greater than 0",
            "type": "greater_than"
        },
        {
            "loc": ["body", "ticker"],
            "msg": "String should match pattern '^[A-Z0-9.\\=]+$'",
            "type": "value_error.str.regex"
        }
    ]
    exc = RequestValidationError(errors)
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/api/v1/paper/order"

    # Execute the exception handler
    with patch("middleware.exception_handler.logger") as mock_logger:
        response = await handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        
        # Load body data
        import json
        body = json.loads(response.body.decode("utf-8"))
        
        assert body["success"] is False
        assert body["error"] == "Validation failed"
        assert "details" in body
        
        # Verify standardized field-level details mapping
        assert body["details"]["quantity"] == "Input should be greater than 0"
        assert "ticker" in body["details"]
        mock_logger.warning.assert_called_once()

# Import MagicMock and patch for unit test execution
from unittest.mock import MagicMock, patch
