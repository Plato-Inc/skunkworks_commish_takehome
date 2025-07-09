from datetime import timedelta

import pandas as pd

TODAY = pd.Timestamp(2025, 7, 6).date()  # freeze for reproducibility; replace with datetime.utcnow().date()
SAFE_TO_ADVANCE_CAP = 2000
ADVANCE_RATE = 0.8
ELIGIBILITY_DAYS = 7

def compute_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame):
    # 1. Sum payments per policy/agent
    earned = carrier_df.groupby(["policy_id", "agent_id"])["amount"].sum().reset_index()
    earned = earned.rename(columns={"amount": "earned_to_date"})

    # 2. Merge with CRM data (one row per policy)
    policy_summary = pd.merge(crm_df, earned, on=["policy_id", "agent_id"], how="left").fillna(0)

    # 3. Get latest status per policy (from carrier data)
    latest_status = carrier_df.groupby(["policy_id", "agent_id"])["status"].last().reset_index()
    policy_summary = pd.merge(policy_summary, latest_status, on=["policy_id", "agent_id"], how="left")

    # 4. Calculate remaining_expected per policy
    policy_summary["remaining_expected"] = policy_summary["ltv_expected"] - policy_summary["earned_to_date"]

    # 5. Eligibility
    policy_summary["submit_date"] = pd.to_datetime(policy_summary["submit_date"]).dt.date
    policy_summary["eligible"] = (policy_summary["status"] == "active") & (
        policy_summary["submit_date"] <= TODAY - timedelta(days=ELIGIBILITY_DAYS)
    )
    eligible = policy_summary[policy_summary["eligible"]]

    # 6. Safe to advance per agent
    advance = eligible.groupby("agent_id")["remaining_expected"].sum().reset_index()
    advance["safe_to_advance"] = advance["remaining_expected"] * ADVANCE_RATE
    advance["safe_to_advance"] = advance["safe_to_advance"].clip(upper=SAFE_TO_ADVANCE_CAP)

    # 7. Earned per agent
    earned_total = earned.groupby("agent_id")["earned_to_date"].sum().reset_index()

    # 8. Merge results
    result = pd.merge(earned_total, advance.drop(columns="remaining_expected"), on="agent_id", how="left").fillna(0)
    return result.to_dict(orient="records")