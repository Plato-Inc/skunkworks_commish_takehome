
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.quotes import compute_quotes

client = TestClient(app)


def test_basic():
    carrier = pd.DataFrame({
        "policy_id": ["P001", "P001"],
        "agent_id": ["A1", "A1"],
        "paid_date": ["2025-07-01", "2025-08-01"],
        "amount": [200, 200],
        "status": ["active", "active"]
    })
    crm = pd.DataFrame({
        "policy_id": ["P001"],
        "agent_id": ["A1"],
        "submit_date": ["2025-06-15"],
        "ltv_expected": [800]
    })
    result = compute_quotes(carrier, crm)
    assert result[0]["safe_to_advance"] == 320  # 800‑400 earned =400; 0.8×400=320

def test_advance_quote_success():
    """Test successful advance quote request with valid CSV files."""
    carrier_csv = "policy_id,agent_id,paid_date,amount,status\nP001,A1,2025-07-01,200,active"
    crm_csv = "policy_id,agent_id,submit_date,ltv_expected\nP001,A1,2025-06-15,800"
    
    files = {
        "carrier_remittance": ("carrier.csv", carrier_csv, "text/csv"),
        "crm_policies": ("crm.csv", crm_csv, "text/csv")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "generated_at" in data
    assert "quotes" in data
    assert len(data["quotes"]) == 1
    assert data["quotes"][0]["agent_id"] == "A1"


def test_advance_quote_invalid_file_type():
    """Test advance quote request with non-CSV files."""
    files = {
        "carrier_remittance": ("carrier.txt", "some content", "text/plain"),
        "crm_policies": ("crm.txt", "some content", "text/plain")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 400
    assert "CSV files" in response.json()["detail"]


def test_advance_quote_missing_filename():
    """Test advance quote request with files that have no filename."""
    files = {
        "carrier_remittance": ("", "some content", "text/csv"),
        "crm_policies": ("", "some content", "text/csv")
    }
    response = client.post("/v1/advance-quote", files=files)
    assert response.status_code == 422

def test_advance_quote_empty_csv():
    """Test advance quote request with empty CSV files."""
    files = {
        "carrier_remittance": ("carrier.csv", "", "text/csv"),
        "crm_policies": ("crm.csv", "", "text/csv")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_advance_quote_encoding_error():
    """Test advance quote request with non-UTF-8 encoded content."""
    # Create bytes that are not valid UTF-8
    invalid_utf8 = b'\xff\xfe\x00\x00'  # Invalid UTF-8 sequence
    
    files = {
        "carrier_remittance": ("carrier.csv", invalid_utf8, "text/csv"),
        "crm_policies": ("crm.csv", "policy_id,agent_id,submit_date,ltv_expected\nP001,A1,2025-06-15,800", "text/csv")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 400
    assert "UTF-8 encoding" in response.json()["detail"]


def test_advance_quote_mixed_file_types():
    """Test advance quote request with one valid CSV and one invalid file."""
    carrier_csv = "policy_id,agent_id,paid_date,amount,status\nP001,A1,2025-07-01,200,active"
    
    files = {
        "carrier_remittance": ("carrier.csv", carrier_csv, "text/csv"),
        "crm_policies": ("crm.txt", "some text content", "text/plain")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 400
    assert "CSV files" in response.json()["detail"]


def test_advance_quote_case_insensitive_extension():
    """Test that CSV file validation is case insensitive."""
    carrier_csv = "policy_id,agent_id,paid_date,amount,status\nP001,A1,2025-07-01,200,active"
    crm_csv = "policy_id,agent_id,submit_date,ltv_expected\nP001,A1,2025-06-15,800"
    
    files = {
        "carrier_remittance": ("carrier.CSV", carrier_csv, "text/csv"),
        "crm_policies": ("crm.Csv", crm_csv, "text/csv")
    }
    
    response = client.post("/v1/advance-quote", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
