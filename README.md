# skunkworks_commish Commission Engine – Take‑Home Assignment

**Estimated effort:** ≈5 focused hours (this assignment is paid).  
---

## 1 · Context

If you're hired, you'll be leading the engineering efforts of project **skunkworks_commish**. Our first milestone in the skunkworks_commish Statement‑of‑Work is an **instant‑pay / commission‑advance engine**. 

Our partner employs agents who sell Medicare policies to the age eligible. Insurance carriers (Humana, UHC, etc.) pay the commission over several months. The goal with skunkworks_commish is to front a portion so the agent gets cash today. The idea is to encourage more effective agent selling behavior by allowing them to extract their earnings close to when they earn them vs waiting two weeks for regular payroll. The challenge is their commission **today** is based on what they sell across the whole pay period. This is called tiered compensation. E.g., if the agent sells 10 policies, they get 1% commission; If they sell 11-20 policies, they get 2%, etc. It's therefore essential to reliably predict how many policies an agent will sell over the whole pay period for every day of the pay period. Having this will allow skunkworks_commish to distribute a portion of the commisions without having to ask for it back in the event the agent doesn't in fact sell what they were expected to.  


We’ve provided a **runnable skeleton** so you can concentrate on the *interesting* problems instead of boilerplate.

---

## 2 · Your Mission 

| Area | Your TODOs |
|------|-----------|
| **Business logic** | Complete `compute_quotes()` so it handles <br>• cancelled → claw‑back scenarios<br>• duplicate or late carrier payments<br>• retro policy status changes (active → cancelled)<br>• edge‑case caps (agent exceeds $2 000 cap across multiple submissions) |
| **Data validation** | Reject malformed CSVs (missing columns, bad dates, negative amounts). Add clear error messages. |
| **Architecture** | Refactor `app/main.py` into sensible modules / layers. Add logging, configuration via env vars, and graceful exception handling. |
| **Testing** | Expand `tests/` to cover happy path **and** at least 3 edge cases (see business logic). Ensure `pytest` passed in CI. |
| **Infrastructure‑as‑Code** | Enhance `infra/main.bicep` *or* replace with Terraform:<br>• parameterize secrets and image tag<br>• enable logging & app‑insights<br>• output the API endpoint URL.<br>Optional: GitHub Action that builds and deploys on push. |
| **Documentation** | Update this `README.md` with:<br>• Setup & run instructions < 10 min<br>• Design / trade‑off decisions<br>• “Next two‑week roadmap” ‑ what you’d tackle next and why.  |
| **Stretch / polish (optional)** | Examples: typed Python (mypy), data streaming instead of pandas, CI workflow, OpenAPI doc tweaks, caching layer, ADR markdowns. • "How you'd improve this takehome". We score *thoughtful* extras higher than volume. |

You’ll find **`TODO:` markers** sprinkled through the code as starting points. Feel free to restructure entirely.

---

## 3 · Input Data

Sample CSVs live in `sample_data/`.  Schema:

| carrier_remittance.csv | crm_policies.csv |
|------------------------|------------------|
| `policy_id`            | `policy_id` |
| `agent_id`             | `agent_id` |
| `paid_date`            | `submit_date` |
| `amount`               | `ltv_expected` |
| `status` (`active|cancelled`) | |

*You may add columns if your solution benefits.*

---

## 4 · Rules Summary

1. **Earned to date** per policy = Σ payments received.  
2. **Remaining expected** = `ltv_expected − earned_to_date`.  
3. A policy is **advance‑eligible** when `status = active` **AND** `submit_date ≤ today − 7 days`.  
4. **Safe‑to‑advance** per agent = `min( 0.80 × Σ remaining_expected (eligible), 2 000 USD cap )`.

We freeze **today** to `2025‑07‑06` in the skeleton for unit‑test reproducibility. You may switch to `datetime.utcnow()`; just adapt your tests.

---

## 5 · Deliverables Checklist 

- [ ] Working API `POST /advance-quote` (multipart: two CSVs) returning per‑agent JSON.
- [ ] All mandatory TODOs above addressed.
- [ ] Tests: `pytest -q` passes.
- [ ] IaC: `az deployment group create …` (or `terraform apply`) provisions resources.
- [ ] Updated README with your notes.
- [ ] (Optional) CI workflow file in `.github/workflows/`.

---

## 6 · Running Locally

```bash
# Option A: Docker
docker compose up --build

# Option B: Local
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest -q
```

---

## 7 · Deployment Example (Bicep)

```bash
az group create -l eastus -n skunkworks_commish-takehome-rg
az deployment group create   --resource-group skunkworks_commish-takehome-rg   --template-file infra/main.bicep   --parameters containerImage=ghcr.io/your-org/skunkworks_commish-api:latest
```

---

## 8 · Scoring Rubric (100 pts)

| Area | Pts |
|------|-----|
| Correctness (business logic) | 30 |
| Code quality & organization  | 20 |
| Tests (coverage & clarity)   | 10 |
| IaC robustness               | 10 |
| Documentation & developer experience | 10 |
| Trade‑off / roadmap memo     | 10 |
| Stretch polish               | 10 |

We value **clarity, reasoning, and sensible trade‑offs** over lines of code.

---

### Good luck! We’re excited to see your approach!
