import pandas as pd
from app.main import compute_quotes

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
