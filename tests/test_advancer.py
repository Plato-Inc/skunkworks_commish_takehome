import pandas as pd
from app.business_logic import compute_quotes
from app.config import config


def test_basic():
    carrier = pd.DataFrame(
        {
            "policy_id": ["P001", "P001"],
            "agent_id": ["A1", "A1"],
            "paid_date": ["2025-07-01", "2025-08-01"],
            "amount": [200.0, 200.0],
            "status": ["active", "active"],
            "carrier": ["Humana", "Humana"],
        }
    )
    crm = pd.DataFrame(
        {
            "policy_id": ["P001"],
            "agent_id": ["A1"],
            "submit_date": ["2025-06-15"],
            "ltv_expected": [800.0],
        }
    )
    result = compute_quotes(carrier, crm)
    expected_advance = (
        800.0 - 400.0
    ) * config.ADVANCE_PERCENTAGE  # 800‑400 earned =400; config.ADVANCE_PERCENTAGE×400
    assert result[0]["safe_to_advance"] == expected_advance
