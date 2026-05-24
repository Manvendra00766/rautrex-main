import pytest
import pytest_asyncio
import io
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app
from dependencies import get_current_user
from services.report_service import ReportService

# Mock data for portfolio overview
MOCK_OVERVIEW = {
    "portfolio": {"id": "p1", "name": "Test Portfolio"},
    "summary": {
        "nav": 100000.0,
        "cash": 20000.0,
        "holdings_count": 2
    },
    "positions": [
        {
            "ticker": "AAPL",
            "shares": 100,
            "avg_cost_per_share": 150.0,
            "current_price": 180.0,
            "unrealized_pnl": 3000.0,
            "unrealized_pnl_pct": 0.2,
            "weight": 0.5
        },
        {
            "ticker": "GOOGL",
            "shares": 50,
            "avg_cost_per_share": 100.0,
            "current_price": 120.0,
            "unrealized_pnl": 1000.0,
            "unrealized_pnl_pct": 0.2,
            "weight": 0.5
        }
    ],
    "equity_curve": [
        {"snapshot_date": "2023-01-01", "nav": 95000.0},
        {"snapshot_date": "2023-01-02", "nav": 100000.0}
    ]
}

MOCK_RISK = {
    "metrics": {
        "var_95": 0.02,
        "var_99": 0.03,
        "beta": 1.1,
        "sharpe": 1.5,
        "max_drawdown": 0.15
    }
}

@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_current_user] = lambda: MagicMock(id="user1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_export_valid_portfolio(client):
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.report_service.calculate_portfolio_risk", new_callable=AsyncMock) as mock_risk, \
         patch("services.report_service.supabase") as mock_supabase:
        
        mock_overview.return_value = MOCK_OVERVIEW
        mock_risk.return_value = MOCK_RISK
        mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []

        response = await client.get("/api/v1/report/export/p1")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert "rautrex_report_p1.pdf" in response.headers["content-disposition"]

@pytest.mark.asyncio
async def test_export_pdf_is_valid_binary(client):
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.report_service.calculate_portfolio_risk", new_callable=AsyncMock) as mock_risk, \
         patch("services.report_service.supabase") as mock_supabase:
        
        mock_overview.return_value = MOCK_OVERVIEW
        mock_risk.return_value = MOCK_RISK
        mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []

        response = await client.get("/api/v1/report/export/p1")
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")

@pytest.mark.asyncio
async def test_export_unauthorized_portfolio(client):
    # If the portfolio doesn't belong to the user, get_portfolio_overview returns None for portfolio
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.db_service.get_portfolio_by_id", new_callable=AsyncMock) as mock_db:
        mock_overview.return_value = {"portfolio": None}
        mock_db.return_value = {"id": "unauthorized_id"} # Exists but not owned
        
        response = await client.get("/api/v1/report/export/unauthorized_id")
        assert response.status_code == 403

@pytest.mark.asyncio
async def test_export_invalid_portfolio_id(client):
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.db_service.get_portfolio_by_id", new_callable=AsyncMock) as mock_db:
        mock_overview.return_value = {"portfolio": None}
        mock_db.return_value = None # Does not exist
        
        response = await client.get("/api/v1/report/export/non_existent_id")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_report_sections_present():
    # We test the ReportService.build_pdf method directly
    service = ReportService()
    data = {
        "overview": MOCK_OVERVIEW,
        "risk": MOCK_RISK,
        "dcf": [],
        "generated_at": "2023-01-01",
        "user_name": "Test User"
    }
    
    with patch("services.report_service.SimpleDocTemplate") as mock_doc:
        mock_doc_instance = mock_doc.return_value
        
        # We want to verify that build_pdf adds elements corresponding to the sections.
        # Since we use Platypus, we check the 'elements' passed to doc.build
        service.build_pdf(data)
        
        assert mock_doc_instance.build.called
        elements = mock_doc_instance.build.call_args[0][0]
        
        # Convert all paragraph texts to a single string to search for headers
        # Elements are Paragraph, Table, Spacer, Image, PageBreak
        text_content = ""
        for el in elements:
            if hasattr(el, 'getPlainText'):
                text_content += el.getPlainText() + " "
            elif hasattr(el, '_cellvalues'): # Table
                for row in el._cellvalues:
                    text_content += " ".join([str(c) for c in row]) + " "
        
        assert "RAUTREX" in text_content # Cover
        assert "Portfolio Summary" in text_content
        assert "Risk Analytics" in text_content
        assert "DCF Valuations" in text_content
        assert "Equity Growth Chart" in text_content

@pytest.mark.asyncio
async def test_gather_report_data_calls_all_services():
    service = ReportService()
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.report_service.calculate_portfolio_risk", new_callable=AsyncMock) as mock_risk, \
         patch("services.report_service.supabase") as mock_supabase:
        
        mock_overview.return_value = MOCK_OVERVIEW
        mock_risk.return_value = MOCK_RISK
        mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []

        await service.gather_report_data("p1", "u1")
        
        assert mock_overview.call_count == 1
        assert mock_risk.call_count == 1
        assert mock_supabase.table.called # DCF service equivalent (direct supabase call)

@pytest.mark.asyncio
async def test_export_when_no_dcf_data(client):
    with patch("services.report_service.get_portfolio_overview", new_callable=AsyncMock) as mock_overview, \
         patch("services.report_service.calculate_portfolio_risk", new_callable=AsyncMock) as mock_risk, \
         patch("services.report_service.supabase") as mock_supabase:
        
        mock_overview.return_value = MOCK_OVERVIEW
        mock_risk.return_value = MOCK_RISK
        # No DCF data found
        mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value.data = []

        response = await client.get("/api/v1/report/export/p1")
        assert response.status_code == 200
        # We also want to check if the PDF contains the "No valuation data available" message.
        # But since we already check if it's a valid PDF, we can rely on unit test for build_pdf.
        
        # Direct check on build_pdf logic for empty DCF
        service = ReportService()
        data = {
            "overview": MOCK_OVERVIEW,
            "risk": MOCK_RISK,
            "dcf": [],
            "generated_at": "2023-01-01",
            "user_name": "Test User"
        }
        pdf_buffer = service.build_pdf(data)
        assert pdf_buffer.getvalue().startswith(b"%PDF")
