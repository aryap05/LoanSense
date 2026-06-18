# LoanSense — Task 7: React Frontend Technical Summary

This document details the implementation of **Task 7** (React Frontend), outlining the frontend architecture, page components, and five major software bugs/security tradeoffs that were resolved during integration.

---

## 1. Frontend Architecture & Page Scaffolding

We scaffolded the frontend application inside the [frontend/](file:///d:/LoanSense/frontend/) directory using **Vite + React** and styled it with **TailwindCSS** and **Lucide React** icons. 

### Page Components Built
1. **`Dashboard.jsx` ([Dashboard.jsx](file:///d:/LoanSense/frontend/src/pages/Dashboard.jsx)):**
   * Acts as the main application lobby.
   * Displays high-level KPIs: Total Applications, Approvals, Rejections, and Manual Review queue count.
   * Includes the **Recent Assessments** table, which fetches the last 5 transactions and provides direct navigation links, completely bypassing the need to copy-paste UUIDs.
2. **`Assess.jsx` ([Assess.jsx](file:///d:/LoanSense/frontend/src/pages/Assess.jsx)):**
   * A comprehensive loan application form.
   * Collects applicant features: monthly income, loan amount, tenure, existing EMI obligations, employment type, loan purpose, CIBIL score, UPI percentile, transaction count, and free-text notes.
   * Implements frontend validations (CIBIL bounds, positive numeric fields) and routes users to the Verdict page upon submission.
3. **`Verdict.jsx` ([Verdict.jsx](file:///d:/LoanSense/frontend/src/pages/Verdict.jsx)):**
   * Displays the final automated decision: Approved, Flagged for Review, or Rejected.
   * Renders color-coded status banners, confidence gauges, plain-language reasoning, triggered pre-filter rules, and RBI compliance mappings.
4. **`Audit.jsx` ([Audit.jsx](file:///d:/LoanSense/frontend/src/pages/Audit.jsx)):**
   * Serves as a compliance search interface.
   * Pulls and renders the full audit log stream for any given applicant ID, including timestamps, model execution details, and raw JSON payloads in a collapsible UI element.
5. **`Layout.jsx` ([Layout.jsx](file:///d:/LoanSense/frontend/src/components/Layout.jsx)):**
   * A wrapper component containing a responsive sidebar navigation menu.
6. **`client.js` ([client.js](file:///d:/LoanSense/frontend/src/api/client.js)):**
   * Configures Axios with a base backend endpoint url and a timeout of 15 seconds.

---

## 2. Errors Faced & Resolutions

During the API integration phase, several software bugs, layout crashes, and compliance design constraints were encountered and resolved.

### Error 1: API Endpoint Base URL Mismatch (HTTP 404)
* **The Error:** Submitting the application form triggered a network `POST` request to `http://localhost:8000/assess` which resulted in an HTTP 404 Not Found error because the backend routes were wired behind the `/api/v1` router prefix.
* **The Resolution:** Adjusted the Axios baseURL configuration inside [client.js](file:///d:/LoanSense/frontend/src/api/client.js) to append `/api/v1` as the default root path:
  ```javascript
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  ```

### Error 2: Data Schema Mismatch on Verdict Retrieval (`NaN%` / Missing Text)
* **The Error:** The `/verdicts/{applicant_id}` backend endpoint originally returned a raw list of database `AgentVerdict` models. The frontend template, however, expected a single flattened JSON object containing both verdict details (confidence, decision) and applicant details (name, PAN hash) for proper rendering. This mismatch caused the UI to render `NaN%` confidence ratings and blank applicant labels.
* **The Resolution:** We modified the `get_verdicts` endpoint in [verdicts.py](file:///d:/LoanSense/backend/app/routers/verdicts.py) to fetch the latest verdict, extract related applicant features, and return a flattened dictionary mapping exactly to the frontend's expected properties:
  ```python
  return {
      "decision": latest_verdict.decision,
      "confidence_score": latest_verdict.confidence,
      "reasons": [latest_verdict.reason] if latest_verdict.reason else [],
      "rbi_flags": list(latest_verdict.rbi_compliance.keys()) if latest_verdict.rbi_compliance else [],
      "name": applicant.raw_features.get("name", "Unknown"),
      "pan_hash": applicant.hashed_pan
  }
  ```

### Error 3: React White-Screen Crash on Icon Load
* **The Error:** After successfully submitting an application, routing the user to the Verdict screen resulted in a white screen (React runtime crash). The browser console output read:
  `ReferenceError: CheckCircle2 is not defined`
* **The Resolution:** The icon `CheckCircle2` was used inside the compliance mapping component in [Verdict.jsx](file:///d:/LoanSense/frontend/src/pages/Verdict.jsx) but was omitted from the destructured import from `lucide-react`. We added `CheckCircle2` to the list of imported SVG components on line 3 of `Verdict.jsx`.

### Error 4: Audit Search ID Retention (UX Flow Gap)
* **The Error:** Reviewing audit logs was tedious because users had to copy a 36-character UUID from the Verdict screen, navigate to the Audit page, paste the string, and click search. Any typing error broke the fetch.
* **The Resolution:** We updated the link in [Verdict.jsx](file:///d:/LoanSense/frontend/src/pages/Verdict.jsx) to pass the `applicantId` implicitly via the React Router router state:
  ```javascript
  <Link to="/audit" state={{ applicantId }}>View Full Audit Log &rarr;</Link>
  ```
  Then, inside [Audit.jsx](file:///d:/LoanSense/frontend/src/pages/Audit.jsx), we added a `useEffect` hook to intercept the incoming location state. If present, it pre-populates the input box and automatically executes the fetch on render.

### Error 5: Sequential IDs Request vs. IDOR Vulnerability (Security Tradeoff)
* **The Error/Request:** During development, typing or copying UUIDs was identified as a source of friction. A request was made to replace UUIDs with sequential integer IDs (e.g. `/verdicts/1`, `/verdicts/2`) to simplify manual URL entry.
* **The Security Flaw:** Changing to sequential IDs introduces a critical **Insecure Direct Object Reference (IDOR)** vulnerability. In a financial application, sequential IDs allow any authenticated user to guess and access other applicants' credit scores and private assessment histories simply by incrementing the ID.
* **The Resolution:** We rejected the request to keep the codebase secure for recruitment reviews. To resolve the developer UX friction, we:
  1. Built a `/verdicts/recent` endpoint in [verdicts.py](file:///d:/LoanSense/backend/app/routers/verdicts.py) returning the latest 5 assessments.
  2. Implemented a "Recent Assessments" dashboard table in [Dashboard.jsx](file:///d:/LoanSense/frontend/src/pages/Dashboard.jsx) with direct navigation links. This allowed immediate testing of new applications without copy-pasting UUIDs.

---

## Technical Interview Q&A for Task 7

* **Q: Why are UUIDs preferred over sequential integer IDs for API routes in financial applications?**
  * *A:* "Sequential IDs are vulnerable to IDOR (Insecure Direct Object Reference) attacks. An attacker can scrape private records by simply incrementing numbers in URL requests. UUIDs, being 128-bit random numbers, are statistically impossible to guess. While sequential IDs are easier to read during local testing, maintaining UUIDs is a security necessity for banking platforms."
* **Q: How did you handle CORS configuration to connect your React Vite frontend with the FastAPI backend?**
  * *A:* "By default, browsers block web apps from making requests to a different domain (like React on port 5173 calling FastAPI on port 8000) for security. We resolved this by adding the `CORSMiddleware` in FastAPI's `main.py`, explicitly listing `http://localhost:5173` in the `allow_origins` array. This sends the appropriate `Access-Control-Allow-Origin` headers, permitting the browser to execute cross-origin fetches safely."
* **Q: Explain how you passed the applicant's UUID from the Verdict page to the Audit page without forcing the user to manually copy-paste it.**
  * *A:* "We leveraged React Router's location state. Inside the Link component on the Verdict page, we passed the UUID via the `state` property. In the Audit component, we used the `useLocation` hook to check if `location.state` had a value. If found, we pre-filled the search input and triggered the database fetch automatically upon component mount."
* **Q: What is a React runtime crash and how does import hygiene affect it?**
  * *A:* "A runtime crash occurs when React encounters an unhandled JavaScript exception during execution, resulting in a blank white page. This commonly happens due to import hygiene issues, such as referencing an undefined variable or component. For example, using a Lucide icon like `CheckCircle2` in JSX without importing it throws a ReferenceError. We prevent this by enforcing strict import declarations and using ESLint to flag undefined variables during compilation."
