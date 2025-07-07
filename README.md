# Take Home Assignment - Skunkworks-Commish 

## 0 · Motivation

If you're hired, you'll be leading the engineering efforts of project **Skunkworks-Commish**. Our first milestone SOW is a **instant‑pay / commission‑advance engine**. This take home is intended to simulate the work you'll actually be doing on it so you get a sense of what boots on the ground will be like, and we can see your capabilities in a controlled setting.

## 1 · Context

Our partner makes money by selling Medicare policies to the age eligible. His team of agents make commission when they sell policies. Insurance carriers (Humana, UHC, etc.) pay the commission over several months. The goal with Skunkworks-Commish is to front a portion so the agent gets cash today. The idea is to encourage more effective agent selling behavior by allowing them to extract their earnings close to when they earn them vs waiting two weeks for regular payroll. 

The challenge is their commission **today** is based on what they sell across the whole pay period. This is called tiered compensation. E.g., if the agent sells 10 policies, they get 1% commission; If they sell 11-20 policies, they get 2%, etc. It's therefore essential to reliably predict how many policies an agent will sell over the whole pay period for every day of the pay period. Having this will allow Skunkworks-Commish to distribute a portion of the commisions without having to ask for it back in the event the agent doesn't in fact sell what they were expected to. While this will eventually involve some ML, for now that'd be premature optimization. I'd like you to focus on implementing the business rules first.

Below is a **runnable (but extremely scrappy) skeleton** so you can do that without wasting time on boilerplate.

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
| **Stretch / polish (optional)** | typed Python (mypy), data streaming instead of pandas, CI workflow, OpenAPI doc tweaks, caching layer, ADR markdowns. "How you'd improve this takehome". 

We score *thoughtful* extras higher than volume. |

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
| `status` (`active/cancelled`) | |

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
az group create -l eastus -n Skunkworks-Commish-takehome-rg
az deployment group create   --resource-group Skunkworks-Commish-takehome-rg   --template-file infra/main.bicep   --parameters containerImage=ghcr.io/your-org/Skunkworks-Commish-api:latest
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

## 9 · Submission 

1. Follow `CONTRIBUTING.md` where the feature branch is your first initial + last name. E.g., **bdey**.
2. Email **brandon@platostudio.com** you're done. 
3. Brandon will review async, leave commments, and schedule a call for you to explain your work/findings within 12h of submission. 
4. Founders will make decide to make offer or not with 24h after that. 


**Estimated effort:** ≈5 focused hours. This assignment is paid $100/hr capped at $500.  


## 9 · FAQ

A quick reference for the most common questions we see about the take‑home.  

If anything here is unclear, email **brandon@platostudio.com**.

| # | Question | Answer |
|---|--------------------|-------------|
| 1 | **How do I get paid for the take‑home?** | We pay **$100 /hr, up to 5 hours**. Email a simple invoice (PDF or plain email) listing hours worked; we ACH within 3 business days. No NDA or W‑9 needed for this task. |
| 2 | **What counts as DONE?** | Ship a repo that passes the checklist in §5 (working API, tests, IaC that compiles, updated README). Extras are optional brownie points. |
| 3 | **May I change the skeleton (framework, file layout)?** | Absolutely. Keep the `/advance-quote` endpoint and CSV schemas so our grader works, but everything else is fair game. |
| 4 | **Do I need a live Azure subscription for IaC?** | No. Your Bicep/Terraform just needs to validate (`az bicep build` or `terraform validate`). Use dummy parameters; we’ll deploy if needed. |
| 5 | **Do I have to build the tier‑prediction ML model?** | Not for this assignment. Focus only on the safe‑advance logic (`compute_quotes`). Predictive modeling is Phase 2 after hire. But this could be extra brownie points if you have time. |
| 6 | **What does `status` mean in remittances vs CRM?** | In **remittance rows** it’s the status *at the payment time* (may flip later). In **CRM** it’s the latest status. Sort by `paid_date` to find last‑known status. |
| 7 | **How should I handle duplicate payment rows?** | Collapse identical `(policy_id, paid_date, amount)` rows into one logical payment unless you document a better approach in README. |
| 8 | **May I add third‑party libs (Pydantic, Poetry, etc.)?** | Yes, provided `pip install -r requirements.txt` or `docker compose up` works in < 5 min on a clean machine. Keep the dependency list lean. |
| 9 | **Timeline after I submit?** | Within **12 h** you’ll get PR comments + a 30‑min Zoom debrief invite. Offer decision within the following **24 h**. |
| 10 | **How do I test the \$2,000 cap scenario?** | Agent **A001** in the sample data exceeds the cap. Your unit test should assert their `safe_to_advance` is \$2 000. |
| 11 | **What if a cancelled policy already paid multiple installments?** | Treat claw‑backs as **negative payments**. Earned = Σ payments (can be negative). Remaining = max(`ltv_expected − earned`, 0). |
| 12 | **What branch/PR naming do you prefer?** | Create a branch `<initial><lastname>` (e.g., `bdey`). Open a PR to `main`; don’t sweat CI failures—we run our own checks. |


Good luck! We’re excited to see your approach! 