from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

app = FastAPI(title="SMS Commission Engine")

TODAY = datetime(2025, 7, 6).date()  # freeze for reproducibility; replace with datetime.utcnow().date()

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def compute_quotes(carrier_df: pd.DataFrame, crm_df: pd.DataFrame):
    # Merge on policy_id & agent_id for safety
    merged = pd.merge(carrier_df, crm_df, on=["policy_id", "agent_id"], suffixes=("_carrier", "_crm"))
    # Earned to date
    earned = merged.groupby(["policy_id", "agent_id"])["amount"].sum().reset_index(name="earned_to_date")
    merged = pd.merge(merged.drop(columns="amount"), earned, on=["policy_id", "agent_id"])
    merged["remaining_expected"] = merged["ltv_expected"] - merged["earned_to_date"]
    # Advance‑eligibility
    merged["submit_date"] = pd.to_datetime(merged["submit_date"]).dt.date
    merged["eligible"] = (merged["status"] == "active") & (merged["submit_date"] <= TODAY - timedelta(days=7))
    eligible = merged[merged["eligible"]]
    advance = eligible.groupby("agent_id")["remaining_expected"].sum().reset_index()
    advance["safe_to_advance"] = advance["remaining_expected"] * 0.8
    advance["safe_to_advance"] = advance["safe_to_advance"].clip(upper=2000)
    # Earned per agent
    earned_total = merged.groupby("agent_id")["earned_to_date"].sum().reset_index()
    result = pd.merge(earned_total, advance.drop(columns="remaining_expected"), on="agent_id", how="left").fillna(0)
    return result.to_dict(orient="records")

@app.post("/advance-quote")
async def advance_quote(
    carrier_remittance: UploadFile = File(...),
    crm_policies: UploadFile = File(...)
):
    for f in (carrier_remittance, crm_policies):
        if not f.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Both uploads must be CSV files.")
    # Read into pandas
    carrier_df = pd.read_csv(StringIO((await carrier_remittance.read()).decode()))
    crm_df = pd.read_csv(StringIO((await crm_policies.read()).decode()))
    quotes = compute_quotes(carrier_df, crm_df)
    return {"generated_at": str(datetime.utcnow()), "quotes": quotes}
