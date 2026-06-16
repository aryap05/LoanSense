# LoanSense — Domain Research

> **Purpose:** Knowledge foundation for the attack generator, contradiction detector, and explainability layer.
> Sources are cited inline. Where a primary source could not be located, the fact is flagged as **⚠ UNVERIFIED — needs manual check**.

---

## 1. India-Specific Synthetic Identity Fraud Patterns

### Pattern 1: Stolen PAN + Fabricated Employment

**Attacker's goal:** Obtain a high-value unsecured loan (personal/business) using a genuine PAN linked to a real person's credit history, paired with fabricated employment and income documentation.

**How it works:**
1. Attacker obtains a valid PAN — sourced from data breaches, document scraping, or purchased from the dark web. Victims are often individuals who rarely check their credit reports: rural populations, the elderly, minors, or the deceased.
2. Attacker fabricates employment documents: fake salary slips, fake Form 16, fake employer letterhead. Sophisticated operations create fake company domains and provide controlled phone numbers for "employer verification" callbacks.
3. Attacker opens a new bank account using the stolen PAN and a fabricated address proof (utility bill, rental agreement).
4. Attacker applies for a loan at an NBFC, presenting the stolen PAN (which pulls the victim's clean CIBIL history) alongside the fabricated employment documentation.
5. Upon disbursement, the attacker withdraws or transfers funds and abandons the account.

**Data signals that betray the fraud:**
- **High CIBIL score + very new account age:** The PAN has a long credit history, but the bank account used for EMI is only 2–5 months old. A genuine person with a 750+ CIBIL score would have established banking relationships.
- **Income-transaction mismatch:** Declared income is ₹80K–₹1.5L/month, but UPI/IMPS transaction history on the linked account shows very low volume (5th–20th percentile). The account is not being used for the spending one would expect at that income level.
- **Generic employer description:** Employer verification details are vague — "Works at private company" rather than a specific, verifiable entity with a GST registration.
- **income_transaction_ratio > 8:** Declared monthly income far exceeds any evidence of actual economic activity in the transaction history.

**Sources:** amlegals.com (SIF in Indian financial sector); ongrid.in (fabricated employment in Indian lending); medium.com/@Deepvue (PAN verification gaps in NBFC lending)

---

### Pattern 2: Fragmented Bureau Footprint

**Attacker's goal:** Accumulate maximum unsecured credit across multiple lenders simultaneously, then default on all obligations ("bust out").

**How it works:**
1. Attacker — often a real person committing first-party fraud — has a thin or no credit file (CIBIL score 0/NA or 300–400).
2. Attacker submits loan applications to 6–12 NBFCs and fintech lenders within a 30-day window, targeting lenders known to have lenient underwriting (typically small NBFCs and microfinance institutions).
3. Because credit bureau data updates are not real-time (updates lag by days to weeks), the early lenders do not see the applications submitted to other lenders.
4. Each lender sees a "thin file" applicant with a moderate income and a single large loan ask — individually plausible, but the aggregate leverage is far beyond repayment capacity.
5. Attacker receives disbursements from multiple lenders, makes zero or minimal repayments, and defaults.

**Data signals that betray the fraud:**
- **High enquiry count (6–12 in 30 days) on a thin file:** A new-to-credit applicant would not normally be shopping across many lenders simultaneously. This "credit hunger" pattern is a known indicator.
- **No file / very low CIBIL (0 or 300–400) + large loan ask (₹3L–₹10L):** The ask is disproportionate to the credit track record.
- **new_to_credit = True + account_age_months < 3:** No established financial relationships.
- **Moderate income that appears individually plausible:** The attacker is not fabricating income — they're exploiting the information lag between lenders.

**Sources:** airtel.in (hard enquiry mechanics); kyckart.com (overlap borrower delinquency in NBFC/MFI); indianexpress.com (bust-out fraud in India); basicroots.in (fragmented bureau issues for NBFCs)

---

### Pattern 3: UPI/IMPS Velocity Spike

**Attacker's goal:** Use a legitimate-looking applicant profile as a mule account for layering illicit funds, then apply for credit to extract additional value before the account is frozen.

**How it works:**
1. Attacker has a clean or semi-clean credit profile — may be their own real identity or a complicit individual.
2. In the 30–60 days before the loan application, the account receives a sudden surge of UPI/IMPS credits from multiple sources (other mule accounts, fraud proceeds). The account then rapidly disburses these funds onward.
3. The "velocity spike" is the signature: the account goes from normal transaction patterns (e.g., 5–10 transactions/month) to hundreds of transactions in a short window.
4. After the burst, the attacker applies for a personal loan or credit line. Their credit profile looks clean — the transaction surge is not visible to the credit bureau, only to the bank holding the account.
5. If approved, the attacker takes the loan and abandons the identity.

**Data signals that betray the fraud:**
- **UPI velocity percentile > 95th:** Transaction volume is in the extreme right tail of the distribution.
- **transaction_velocity_30d = 3x–10x their historical average:** Dramatic deviation from baseline behavior.
- **income_transaction_ratio < 0.5:** Transaction volume *exceeds* declared income — the account is moving more money than the applicant claims to earn, suggesting external fund flows.
- **Otherwise clean profile:** Credit score is fine, employment is fine — the fraud signal is entirely in the transaction behavior. This is why siloed models miss it.

**Sources:** precisa.in (mule account velocity patterns); raptorx.ai (burst patterns in UPI fraud); RBI's MuleHunter.AI initiative (PIB, Government of India); stripe.com (velocity rules in fraud detection); zethic.com (unified intelligence layer for mule detection)

---

### Pattern 4: Synthetic Identity — Clean Constructed Profile

**Attacker's goal:** Create a completely fabricated identity that passes all individual checks — no single red flag — then obtain and default on a large loan.

**How it works:**
1. Attacker constructs a new identity from scratch: a real PAN (possibly obtained from a deceased or inactive person), a fabricated name, a new phone number, a rented address.
2. Attacker "seasons" the identity over 2–6 months: opens a bank account, takes a small secured credit card (backed by FD), makes regular small purchases, pays on time. This builds a clean — but very short — credit history.
3. After the seasoning period, the attacker has a CIBIL score in the 720–780 range (achievable with 2–3 months of perfect repayment on a secured card).
4. Attacker applies for a larger unsecured loan. Every individual check passes: income is reasonable, CIBIL is good, employment is plausible, no fraud flags fire.
5. The only anomaly is **recency**: account age is 2–4 months across *all* financial products. No relationship older than 6 months exists anywhere.

**Data signals that betray the fraud:**
- **CIBIL score 720–780 with account_age_months = 2–4:** This combination is almost impossible organically. Building a 720+ score requires years of credit history, not months.
- **new_to_credit = True despite good score:** The score is high, but the *depth* of the file is extremely shallow.
- **Low enquiry count (1–2 in 30 days):** Unlike the bust-out pattern, the careful attacker does not shop around. They target one lender with a well-crafted application.
- **No single red flag fires:** This is why the contradiction detector exists. The credit model sees a good applicant. The fraud model sees no fraud signals. Only the cross-signal analysis — "high score + new account across all products" — catches the inconsistency.

**Sources:** innovatrics.com (synthetic identity fraud lifecycle); amlegals.com (SIF seasoning phase in India); shuftipro.com (SIF bust-out cycle); ondato.com (Frankenstein identity construction)

---

## 2. RBI Fair Practices Code — Relevant Sections

### Governing Document

**Master Direction – Reserve Bank of India (Non-Banking Financial Company – Scale Based Regulation) Directions, 2023**
- Circular: RBI/DoR/2023-24/106
- Reference: DoR.FIN.REC.No.45/03.10.119/2023-24
- Date: October 19, 2023 (Updated as on July 17, 2025)
- Chapter VII covers **Fair Practices Code** for NBFCs.

The original FPC guidelines for NBFCs were issued via circular **DNBS.CC.PD.No.266/03.10.01/2011-12** and have been consolidated into the SBR Master Directions.

### Section: Communication of Rejection Reasons

**Requirement (Chapter VII, Fair Practices Code):**

> NBFCs shall convey in writing the main reason(s) for rejection of a loan application to the applicant.

Key obligations:
1. **Written communication is mandatory** — oral communication is insufficient.
2. **Reasons must be stated** — a bare rejection without reasoning does not comply.
3. **Timeliness** — communication must be provided within the timeframe defined in the NBFC's board-approved lending policy.
4. **Language** — should be in a language understood by the borrower; vernacular language if applicable.

**LoanSense relevance:** The `primary_reason` field in the agent verdict schema directly satisfies this requirement. Every REJECT or FLAG_FOR_REVIEW decision produces a plain-language explanation mapped to this RBI section.

### Section: KYC Verification

**Governing Document:** Master Direction – Know Your Customer (KYC) Direction, 2016 (as updated)

Key requirements:
1. **Customer Due Diligence (CDD)** is mandatory before extending any credit facility.
2. **No application shall be rejected without application of mind** — the officer must record specific reason(s) for any KYC rejection.
3. **Verification against original documents** is required — photocopies or digital scans alone are insufficient for high-value transactions.
4. **Periodic KYC updates** — existing customers must undergo KYC renewal at prescribed intervals.

**LoanSense relevance:** When the contradiction detector flags a synthetic identity pattern (high CIBIL + new account), the verdict maps to this KYC section — recommending manual verification of PAN and address proof against original documents.

### Section: Automated Credit Decisions

There is no single RBI section exclusively governing automated credit decisions. However:
1. **All credit decisions — manual or automated — must comply with a board-approved credit policy** (SBR Master Directions, Chapter on Governance).
2. **Digital Lending Guidelines (September 2, 2022):** For loans originated via digital platforms, RBI mandates that the name of the lending NBFC must be disclosed, and borrowers must receive transparent reasons for credit decisions.
3. **Algorithmic transparency:** While not yet explicitly mandated for NBFCs, RBI has signaled (via consultation papers) an expectation that automated decision systems should be auditable and explainable.

**LoanSense relevance:** The full audit trail (model calls, scores, rule flags, agent reasoning) stored in `audit_logs` provides the auditability that RBI's direction of travel demands.

> **⚠ NOTE:** Specific section numbers within Chapter VII of the SBR Master Direction were not extractable from the RBI website (the page renders content dynamically). The requirements above are accurately paraphrased from the regulatory framework. For production compliance, obtain the full PDF from [RBI Master Directions page](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12550) and verify exact section numbers.

---

## 3. NBFC Lending Context

### What a Loan Officer Actually Does During Manual Underwriting

A loan officer at a small NBFC in India typically follows this workflow:

**Step 1 — Application Intake & KYC**
- Collects identity documents: PAN card, Aadhaar card, passport/voter ID.
- Collects address proof: utility bills, rental agreement, bank statement with address.
- For salaried applicants: last 3–6 months' salary slips, Form 16, employer letter.
- For self-employed: last 2–3 years' ITR, GST registration, bank statements.
- Performs visual document verification — checks for obvious tampering, consistency of name/address across documents.

**Step 2 — Bureau Pull**
- Pulls CIBIL report (or Experian/Equifax) using PAN.
- Reviews: score, active loan accounts, payment history (DPD — Days Past Due), enquiry history.
- At small NBFCs, this is often a single bureau pull. Larger lenders do multi-bureau checks.

**Step 3 — Income Assessment**
- Calculates EMI-to-income ratio (typically must be ≤ 50–60% of net monthly income including existing EMIs).
- For salaried: verifies salary credit in bank statement matches salary slip.
- For self-employed: assesses average monthly income from bank statement turnover and ITR.
- **This is where fraud most commonly enters:** the officer is comparing declared income against documents that may be fabricated.

**Step 4 — Risk Assessment & Decision**
- Applies internal credit policy: minimum CIBIL score thresholds, maximum loan-to-income ratios, sector/geography limits.
- Uses personal judgment for borderline cases — "Does this application feel right?"
- Prepares recommendation (approve/reject/modify terms) for the credit committee or branch manager.

### Data Typically Available to the Officer

| Data Source | What It Contains | Limitations |
|-------------|-----------------|-------------|
| CIBIL/Experian report | Score, active accounts, payment history, enquiry count | Lags real-time by days/weeks; doesn't include informal lending |
| Bank statements (3–6 months) | Salary credits, spending patterns, balance history | Can be fabricated; officer relies on visual inspection |
| Salary slips / Form 16 | Income verification for salaried | Easily forged with modern tools |
| ITR / GST returns | Income verification for self-employed | May understate actual income; or may be fabricated |
| Employer verification | Phone call to stated employer | Fraudsters provide controlled numbers |
| Address verification | Physical visit or digital verification | Often outsourced to agencies with variable quality |
| UPI/IMPS transaction data | **NOT typically available** to the loan officer | This is a critical gap — transaction behavior is held by the applicant's bank, not the lending NBFC |

### Common Failure Modes (Where Officers Miss Fraud)

1. **Reliance on forged documents:** Modern forgery tools produce salary slips, bank statements, and Form 16s that are visually indistinguishable from genuine documents. A human officer reviewing hundreds of applications per week cannot catch metadata-level inconsistencies.

2. **Information silos:** The loan officer sees the CIBIL report and the applicant's documents, but cannot cross-reference against the applicant's actual bank transaction data (held by a different institution), GST filings (held by GSTN), or employer payroll records. Each document is reviewed in isolation.

3. **Volume pressure:** Small NBFCs process 500–2,000 applications per month with limited staff. Officers face implicit pressure to approve (commission structures often reward disbursement volume), leading to superficial reviews on borderline cases.

4. **No transaction behavior analysis:** The officer has no visibility into UPI/IMPS transaction patterns. A mule account with a massive velocity spike looks like a normal bank account on the CIBIL report.

5. **No cross-lender visibility in real-time:** When a bust-out attacker applies to 8 lenders simultaneously, each officer sees only their own application. The CIBIL enquiry count updates with a lag, so the first 3–4 lenders may not see the subsequent applications.

6. **Internal collusion:** In some cases, loan officers at small NBFCs are complicit — either incentivized by the fraudster or operating under management pressure to hit disbursement targets. RBI's 2024 Fraud Risk Management Directions for NBFCs specifically address this.

**Sources:** RBI Master Directions on Fraud Risk Management for NBFCs (July 2024); nishithdesai.com (NBFC fraud governance); wrightresearch.in (NBFC delinquency analysis); kyckart.com (overlap borrower problem in MFI/NBFC)

---

## 4. CIBIL Score Ranges and Industry Interpretation

### Score Range: 300–900

CIBIL (TransUnion CIBIL) scores in India range from **300 to 900**. The score is calculated based on the individual's credit history as reported by lenders to the bureau.

| Score Range | Rating | Industry Interpretation | Typical Lending Action |
|------------|--------|------------------------|----------------------|
| **750–900** | Excellent | High creditworthiness. Strong repayment history, low utilisation. | Loan approval at best available interest rates. Minimal documentation. |
| **700–749** | Good | Positive credit behavior. Minor blemishes acceptable. | Approval likely. Standard interest rates. Full documentation. |
| **650–699** | Fair | Some risk indicators. Late payments or high utilisation present. | Approval possible at higher interest rates. Additional income verification may be required. |
| **600–649** | Doubtful | Significant credit issues. Multiple late payments or defaults. | Most mainstream lenders reject. Some NBFCs/fintechs may consider with collateral or guarantor. |
| **Below 600** | Poor | Severe credit issues. Active defaults or settlements on record. | Rejection from nearly all regulated lenders. |

**Sources:** cibil.com (official score interpretation); moneyview.in (score bands); hdfcbank.in (lending criteria); kotakbank.in (score interpretation guide)

### Thin File and No File (NA/NH)

- **NH (No History):** The individual exists in the bureau's database but has no credit accounts — never taken a loan, never had a credit card. Display shows "NH" instead of a numeric score.
- **NA (Not Applicable):** Insufficient data to generate a score — typically fewer than 6 months of credit history or no activity in the recent period.
- **Thin File:** A credit report that exists but contains very few accounts (typically < 3 active accounts) or a very short history (< 12 months). A numeric score may be generated, but it is based on limited data and may not be reliable.

**How Indian lenders treat thin/no file applicants:**
- Traditional banks typically reject or require a guarantor/collateral.
- Fintechs and progressive NBFCs use alternative data (bank statement analysis, UPI transaction patterns, digital footprint) to underwrite thin-file applicants.
- Secured credit cards (backed by fixed deposit) are the standard "starter" product for building a first credit file.

**⚠ Critical for LoanSense:** A CIBIL score of 0 (used in the codebase to represent NH/NA) must be treated differently from a score of 300. A score of 0 means "no data" — it could be a genuine first-time borrower or a synthetic identity that hasn't been used for credit yet. The contradiction detector handles this by flagging `new_to_credit = True` as a modifier that changes the interpretation of other signals.

### Score Distribution in Indian Lending

| Segment | Approximate Distribution | Notes |
|---------|-------------------------|-------|
| No file (NH/NA) | ~15–20% of adult population | Higher in rural areas, younger demographics |
| 300–599 (Poor) | ~25–30% of scored population | **⚠ UNVERIFIED — industry estimate, not official CIBIL data** |
| 600–749 (Fair to Good) | ~35–40% | Bulk of the lending market |
| 750–900 (Excellent) | ~15–20% | Premium borrowers |

> **⚠ UNVERIFIED:** Exact distribution percentages are not published by CIBIL. The above are industry estimates from multiple lending industry sources and should be validated against actual NBFC portfolio data before being used for synthetic data generation parameters.

**Sources:** cibil.com (NH/NA definitions); smfgindiacredit.com (score factors); experian.com (thin file definition); stashfin.com (building credit from NH/NA); piramalfinance.com (CIBIL score ranges)

---

## Summary: Key Implications for LoanSense Design

| Research Finding | Design Implication |
|-----------------|-------------------|
| Stolen PAN fraud relies on income-transaction mismatch | `income_transaction_ratio` is a critical feature; must be a cross-signal, not an individual model feature |
| Bureau data lags real-time by days | `enquiry_count_30d` is a lagging indicator; must be combined with other signals for bust-out detection |
| UPI velocity spikes are invisible to credit bureaus | Transaction velocity features must be in the fraud model, not the credit model |
| Synthetic identities pass all individual checks | The contradiction detector (cross-signal analysis) is the only layer that can catch Pattern 4 |
| RBI requires written rejection reasons | `primary_reason` and `rbi_mapping` in the verdict schema are not optional — they're regulatory requirements |
| Officers lack cross-institution visibility | LoanSense simulates what a system with unified data access could detect |
| CIBIL score 0 ≠ CIBIL score 300 | `new_to_credit` flag must be treated as a distinct signal, not just "low score" |
| Fabricated documents are visually convincing | The system cannot rely on document verification; must use behavioral and statistical signals |
