
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quotes import compute_quotes

client = TestClient(app)

# === Fixtures ===
@pytest.fixture
def valid_carrier_csv():
    return "policy_id,agent_id,paid_date,amount,status\nP001,A1,2025-07-01,200,active"

@pytest.fixture
def valid_crm_csv():
    return "policy_id,agent_id,submit_date,ltv_expected\nP001,A1,2025-06-15,800"

# === Helper ===
def post_advance_quote(carrier, crm):
    files = {
        "carrier_remittance": ("carrier.csv", carrier, "text/csv"),
        "crm_policies": ("crm.csv", crm, "text/csv")
    }
    return client.post("/v1/advance-quote", files=files)

# === API Success Tests ===
class TestAdvanceQuoteSuccess:
    def test_basic(self, valid_carrier_csv, valid_crm_csv):
        """Test successful advance quote request with valid CSV files."""
        response = post_advance_quote(valid_carrier_csv, valid_crm_csv)
        assert response.status_code == 200
        data = response.json()
        assert "generated_at" in data
        assert "quotes" in data
        assert len(data["quotes"]) == 1
        assert data["quotes"][0]["agent_id"] == "A1"

    def test_case_insensitive_extension(self, valid_carrier_csv, valid_crm_csv):
        """Test that CSV file validation is case insensitive."""
        files = {
            "carrier_remittance": ("carrier.CSV", valid_carrier_csv, "text/csv"),
            "crm_policies": ("crm.Csv", valid_crm_csv, "text/csv")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "quotes" in data

# === API Validation/Error Tests ===
class TestAdvanceQuoteValidation:
    def test_invalid_file_type(self):
        """Test with non-CSV files."""
        files = {
            "carrier_remittance": ("carrier.txt", "some content", "text/plain"),
            "crm_policies": ("crm.txt", "some content", "text/plain")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 400
        assert "CSV files" in response.json()["detail"]

    def test_missing_filename(self):
        """Test with files that have no filename."""
        files = {
            "carrier_remittance": ("", "some content", "text/csv"),
            "crm_policies": ("", "some content", "text/csv")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 422

    def test_empty_csv(self):
        """Test with empty CSV files."""
        files = {
            "carrier_remittance": ("carrier.csv", "", "text/csv"),
            "crm_policies": ("crm.csv", "", "text/csv")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"]

    def test_encoding_error(self, valid_crm_csv):
        """Test with non-UTF-8 encoded content."""
        invalid_utf8 = b'\xff\xfe\x00\x00'
        files = {
            "carrier_remittance": ("carrier.csv", invalid_utf8, "text/csv"),
            "crm_policies": ("crm.csv", valid_crm_csv, "text/csv")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 400
        assert "UTF-8 encoding" in response.json()["detail"]

    def test_mixed_file_types(self, valid_carrier_csv):
        """Test with one valid CSV and one invalid file."""
        files = {
            "carrier_remittance": ("carrier.csv", valid_carrier_csv, "text/csv"),
            "crm_policies": ("crm.txt", "some text content", "text/plain")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code == 400
        assert "CSV files" in response.json()["detail"]

    def test_invalid_csv_format(self, valid_crm_csv):
        """Test with malformed CSV content."""
        # pandas is lenient, so this may not always fail
        carrier_csv = "policy_id,agent_id,paid_date,amount,status\nP001,A1,2025-07-01,200,active\nP002,A2,2025-07-02,300"
        files = {
            "carrier_remittance": ("carrier.csv", carrier_csv, "text/csv"),
            "crm_policies": ("crm.csv", valid_crm_csv, "text/csv")
        }
        response = client.post("/v1/advance-quote", files=files)
        assert response.status_code in [200, 400]

# === Pure Function Test ===
def test_compute_quotes_basic():
    """Test compute_quotes business logic directly."""
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

def test_compute_quotes_sample_data():
    """Test compute_quotes with the sample_data CSV files and compare to expected response."""
    import json
    import os

    import pandas as pd
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_data")
    carrier_path = os.path.abspath(os.path.join(sample_dir, "carrier_remittance.csv"))
    crm_path = os.path.abspath(os.path.join(sample_dir, "crm_policies.csv"))
    response_path = os.path.abspath(os.path.join(sample_dir, "sample_response.json"))
    carrier = pd.read_csv(carrier_path)
    crm = pd.read_csv(crm_path)
    with open(response_path) as f:
        expected = json.load(f)
    result = compute_quotes(carrier, crm)
    # Sort both lists by agent_id for comparison
    result_sorted = sorted(result, key=lambda x: x["agent_id"])
    expected_sorted = sorted(expected, key=lambda x: x["agent_id"])
    assert result_sorted == expected_sorted
