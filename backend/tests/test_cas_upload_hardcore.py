import io
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pdfplumber.utils.exceptions import PdfminerException

from main import app
from auth import get_current_user  # Import from auth to correctly override dependency in onboarding.py
from services.cas_parser import parse_cas_pdf

# --- 1. REPORTLAB MOCK PDF GENERATION UTILITY ---

def generate_mock_cas_pdf(password: str = None) -> bytes:
    """
    Dynamically generates a real PDF document containing CDSL/NSDL CAS layout text
    with standard Indian ISINs and holdings to test pdfplumber parsing.
    """
    buffer = io.BytesIO()
    
    # In ReportLab, encryption is supplied in the Canvas constructor
    c = canvas.Canvas(buffer, pagesize=letter, encrypt=password)
    
    # Draw mock CAS header and holding rows
    c.drawString(100, 750, "CENTRAL DEPOSITORY SERVICES (INDIA) LIMITED")
    c.drawString(100, 730, "Consolidated Account Statement (CAS)")
    c.drawString(100, 700, "-------------------------------------------------------------")
    
    # Holding 1: TCS Equity (ISIN: INE467B01029)
    # format: name, isin, shares, cost, price
    c.drawString(100, 650, "TCS TATA CONSULTANCY SERVICES LTD  INE467B01029  150.0  3250.50  3400.00")
    
    # Holding 2: Reliance Equity (ISIN: INE002A01018)
    c.drawString(100, 620, "RELIANCE INDUSTRIES LTD       INE002A01018  250.0  2200.00  2450.25")
    
    # Holding 3: Parag Parikh Mutual Fund (ISIN: INF200K01UV4)
    c.drawString(100, 590, "PARAG PARIKH FLEXI CAP FUND    INF200K01UV4  500.0  45.50    58.75")
    
    c.drawString(100, 500, "-------------------------------------------------------------")
    c.drawString(100, 480, "End of Statement. Thank you.")
    
    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# --- 2. FASTAPI MOCK AUTHENTICATION ENVIRONMENT ---

class MockUser:
    id = "test-quant-user-456"
    email = "quant@rautrex.com"

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

# --- 3. HARDCORE TEST CASES ---

def test_cas_parser_success_unencrypted():
    """
    Test 1: Verifies that our parser successfully extracts stock/fund ISINs, 
    quantities, sectors, and values from a plain unencrypted PDF.
    """
    pdf_bytes = generate_mock_cas_pdf()
    
    holdings = parse_cas_pdf(pdf_bytes)
    assert len(holdings) == 3
    
    # Verify TCS details (TCS mapped to TCS.NS)
    tcs = next(h for h in holdings if "TCS" in h["ticker"])
    assert tcs["shares"] == 150.0
    assert tcs["avg_cost"] == 3250.50
    assert tcs["asset_type"] == "equity"
    assert tcs["sector"] == "Technology"
    
    # Verify Reliance details (Reliance mapped to RELIANCE.NS)
    reliance = next(h for h in holdings if "RELIANCE" in h["ticker"])
    assert reliance["shares"] == 250.0
    assert reliance["avg_cost"] == 2200.00
    assert reliance["sector"] == "Energy/Conglomerate"
    
    # Verify Mutual Fund details
    fund = next(h for h in holdings if h["asset_type"] == "mutual_fund")
    assert fund["shares"] == 500.0
    assert fund["avg_cost"] == 45.50
    assert fund["sector"] == "Diversified Mutual Fund"


def test_cas_parser_success_encrypted():
    """
    Test 2: Verifies that an encrypted, password-protected CAS PDF is decrypted 
    and parsed correctly when supplied with the correct password.
    """
    pan_password = "ABCDE1234F"
    pdf_bytes = generate_mock_cas_pdf(password=pan_password)
    
    holdings = parse_cas_pdf(pdf_bytes, password=pan_password)
    assert len(holdings) == 3
    
    tcs = next(h for h in holdings if "TCS" in h["ticker"])
    assert tcs["shares"] == 150.0
    
    reliance = next(h for h in holdings if "RELIANCE" in h["ticker"])
    assert reliance["shares"] == 250.0


def test_cas_parser_incorrect_password():
    """
    Test 3: Verifies that passing an incorrect password to an encrypted CAS PDF
    raises a PdfminerException during extraction decryption failure.
    """
    pdf_bytes = generate_mock_cas_pdf(password="RIGHT_PASSWORD")
    
    with pytest.raises(PdfminerException):
        parse_cas_pdf(pdf_bytes, password="WRONG_PASSWORD")


def test_api_upload_cas_route():
    """
    Test 4: Integration test that mocks a user uploading a CAS PDF via the HTTP POST
    route `/api/v1/onboarding/upload-cas` and asserts a 200 OK with correct schema.
    """
    pdf_bytes = generate_mock_cas_pdf()
    
    # Submit the PDF as a multi-part file upload with authorization header
    response = client.post(
        "/api/v1/onboarding/upload-cas",
        files={"file": ("cdsl_statement.pdf", pdf_bytes, "application/pdf")},
        data={"password": ""},
        headers={"Authorization": "Bearer mock_token"}
    )
    
    assert response.status_code == 200
    res_data = response.json()
    
    assert res_data["status"] == "success"
    assert res_data["broker"] == "cas_statement"
    assert res_data["holdings_count"] == 3
    
    holdings = res_data["holdings"]
    assert any("TCS" in h["ticker"] for h in holdings)
    assert any("RELIANCE" in h["ticker"] for h in holdings)
    
    # Assert that portfolio analysis metrics exist in the response
    assert "diversification_score" in res_data["analysis"]
