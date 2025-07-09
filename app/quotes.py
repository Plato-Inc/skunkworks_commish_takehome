from datetime import timedelta

import pandas as pd

TODAY = pd.Timestamp(2025, 7, 6).date()  # freeze for reproducibility; replace with datetime.utcnow().date()
SAFE_TO_ADVANCE_CAP = 2000
ADVANCE_RATE = 0.8
ELIGIBILITY_DAYS = 7

def compute_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame):
    # Merge on policy_id & agent_id for safety
    merged = pd.merge(carrier_df, crm_df, on=["policy_id", "agent_id"], suffixes=("_carrier", "_crm"))
    # Earned to date
    earned = merged.groupby(["policy_id", "agent_id"])["amount"].sum().reset_index()
    earned = earned.rename(columns={"amount": "earned_to_date"})
    merged = pd.merge(merged.drop(columns="amount"), earned, on=["policy_id", "agent_id"])
    merged["remaining_expected"] = merged["ltv_expected"] - merged["earned_to_date"]
    # Advance‑eligibility
    merged["submit_date"] = pd.to_datetime(merged["submit_date"]).dt.date
    merged["eligible"] = (merged["status"] == "active") & (merged["submit_date"] <= TODAY - timedelta(days=ELIGIBILITY_DAYS))
    eligible = merged[merged["eligible"]]
    advance = eligible.groupby("agent_id")["remaining_expected"].sum().reset_index()
    advance["safe_to_advance"] = advance["remaining_expected"] * ADVANCE_RATE
    advance["safe_to_advance"] = advance["safe_to_advance"].clip(upper=SAFE_TO_ADVANCE_CAP)
    # Earned per agent
    earned_total = merged.groupby("agent_id")["earned_to_date"].sum().reset_index()
    result = pd.merge(earned_total, advance.drop(columns="remaining_expected"), on="agent_id", how="left").fillna(0)
    return result.to_dict(orient="records")