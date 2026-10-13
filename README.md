# Gift Decision Agent — Intelligent AI Gifting Advisory

> **Agent 2** by Geetha | Powered by LangGraph, Google Gemini, and Deterministic Multi-Attribute Scoring

A full-stack, demo-ready autonomous AI decision-making agent that answers:
> *"What is the best gift for this particular person, occasion, and budget, and why?"*

Unlike generic chat bots that produce random lists of gifts, the **Gift Decision Agent** implements a typed, stateful **LangGraph** multi-stage reasoning workflow. It generates diverse gift candidates, enforces hard constraint boundaries, deterministically scores trade-offs across 5 evaluation dimensions, audits choices via a decision reviewer, and adaptively refines its recommendations when users provide interactive feedback.

---

## Table of Contents
1. [Problem Statement & Core Idea](#1-problem-statement--core-idea)
2. [Key Capabilities & Innovations](#2-key-capabilities--innovations)
3. [Architecture & LangGraph Workflows](#3-architecture--langgraph-workflows)
4. [Hard Constraints vs. Soft Preferences](#4-hard-constraints-vs-soft-preferences)
5. [Deterministic Scoring Formula](#5-deterministic-scoring-formula)
6. [Interactive Feedback & Adaptation Loop](#6-interactive-feedback--adaptation-loop)
7. [Dual Reasoning Modes (Gemini + Deterministic Fallback)](#7-dual-reasoning-modes-gemini--deterministic-fallback)
8. [Project Structure](#8-project-structure)
9. [Local Setup & Installation](#9-local-setup--installation)
10. [Running Automated Tests](#10-running-automated-tests)
11. [Deployment on Render](#11-deployment-on-render)
12. [Input / Output Examples](#12-input--output-examples)
13. [Viva Voce Questions & Answers](#13-viva-voce-questions--answers)
14. [Known Limitations & Disclaimers](#14-known-limitations--disclaimers)

---

## 1. Problem Statement & Core Idea

Gift selection is an inherently complex multi-attribute decision problem. Typical challenges include:
- Budget constraints that must not be exceeded.
- Personal recipient hobbies, lifestyle habits, and tastes.
- Balancing practical daily usefulness against sentimental keepsake value.
- Avoiding generic items (e.g., standard mugs or mass-market chocolates) or items the recipient already owns.
- Recovering gracefully when a suggestion is rejected by understanding *why* and pivoting without repeating identical options.

**The Gift Decision Agent solves this by:**
1. Transforming unstructured gifting requests into a typed, validated state.
2. Generating 5–8 diverse candidates across distinct product/experience categories.
3. Filtering candidates through strict hard constraints before scoring.
4. Calculating a transparent, normalized 100-point score for every candidate.
5. Reviewing the top choice for diversity and appropriateness.
6. Presenting the selected best match alongside viable alternatives, trade-offs, and personalization ideas.
7. Providing a one-click PDF decision report via ReportLab.

---

## 2. Key Capabilities & Innovations

- **Real LangGraph StateGraph Architecture**: Built on actual state transitions and conditional branching rather than static prompt chains.
- **Strict Hard vs. Soft Separation**: Budget ceilings, category exclusions, and previously owned items are strictly enforced before scoring—a candidate exceeding budget will never win simply due to sentimental points.
- **Deterministic 100-Point Scoring Engine**: Transparent Python calculations with full component breakdowns (Interest Match 30%, Budget Fit 25%, Relevance 20%, Purpose Match 15%, Personalization 10%).
- **Interactive Feedback Adaptation**: 1-click rejection controls ("Too expensive", "Already owns it", "Not useful", "Different category", "More creative") that update constraints, exclude rejected candidates, and recalculate scores.
- **100% Reliable Dual-Engine Support**: Operates using Google Gemini (`gemini-2.5-flash`) when configured, with seamless, automatic fallback to an extensive 30+ item curated Indian market catalogue (`INR ₹200–₹35,000+`) if Gemini is unavailable.
- **Professional ReportLab PDF Export**: Instant download of an official executive gift decision brief with tables, breakdowns, and disclaimers.
- **Luxury Cream & Lavender UI**: Elegant warm cream canvas (`#FDFBF7`), royal violet headings (`#4A148C`), vibrant lavender accents (`#6C5CE7`), and accessible responsive design.

---

## 3. Architecture & LangGraph Workflows

### 3.1 Main Recommendation Workflow

```
[START]
   │
   ▼
[Preference Validator] ────────── Validates budget bounds, deduplicates interests
   │
   ▼
[Candidate Generator] ─────────── Synthesizes 5–8 candidates via Gemini or Catalogue
   │
   ▼
[Constraint Filter]
   │
   ├── [Valid Candidates < 3 & Attempts < 3] ──► (Loop back to Candidate Generator)
   │
   ▼ [Valid Candidates >= 3]
[Deterministic Scoring Engine] ── Scores each candidate across 5 dimensions (0–100)
   │
   ▼
[Decision Reviewer] ───────────── Audits budget compliance, diversity, & genericness
   │
   ├── [Review Failed & Attempts < 3] ─────────► (Loop back to Candidate Generator)
   │
   ▼ [Review Passed OR Attempts >= 3]
[Final Recommendation Synthesis] ─ Formats rationale, trade-offs, & alternatives
   │
   ▼
 [END]
```

### 3.2 Adaptive Feedback Workflow

```
[START (User Rejection)]
   │
   ▼
[Feedback Analyzer] ───────────── Decodes rejection reason (e.g. "Too expensive", "Already owns")
   │
   ▼
[Preference/Constraint Updater] ─ Appends to rejected_gifts, tightens budget, excludes category
   │
   ▼
[Candidate Regenerator] ───────── Generates fresh candidate set respecting new exclusions
   │
   ▼
[Constraint Filter] ───────────── Re-applies hard boundaries
   │
   ▼
[Scoring Engine] ──────────────── Recalculates normalized scores with adapted weights
   │
   ▼
[Decision Reviewer] ───────────── Audits updated candidate
   │
   ▼
[Updated Recommendation] ──────── Returns revised top match and explains the shift
   │
   ▼
 [END]
```

---

## 4. Hard Constraints vs. Soft Preferences

| Attribute | Constraint Classification | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Maximum Budget Ceiling** | **Hard Constraint** | Any candidate whose minimum cost exceeds `budget_max` is strictly rejected before scoring. |
| **Excluded Items / Avoid** | **Hard Constraint** | Substrings matching `disliked_items` are eliminated in `Constraint Filter`. |
| **Already Owned Items** | **Hard Constraint** | Items the recipient owns are disqualified immediately. |
| **Mandatory Gift Type** | **Hard Constraint** | If user selects "Handmade" or "Experience", non-matching formats are eliminated. |
| **Previously Rejected Gifts** | **Hard Constraint** | Candidates rejected during interactive feedback cannot be re-recommended. |
| **Interest Alignment** | *Soft Preference* | Scored in the 30% Interest Match component. |
| **Budget Proximity / Value** | *Soft Preference* | Scored in the 25% Budget Fit component (under-budget rewarded, near-max penalized). |
| **Occasion / Relationship** | *Soft Preference* | Scored in the 20% Relevance component. |
| **Gift Purpose (Utility/Sentiment)** | *Soft Preference* | Scored in the 15% Purpose Match component. |
| **Personalization Potential** | *Soft Preference* | Scored in the 10% Personalization component. |

---

## 5. Deterministic Scoring Formula

Every candidate is evaluated in Python using normalized mathematical functions:

$$\text{Total Score} = S_{\text{interest}} + S_{\text{budget}} + S_{\text{relevance}} + S_{\text{purpose}} + S_{\text{personalization}}$$

### Weight Configuration
- **Interest Match (30 pts)**: Ratio of recipient hobbies matched in candidate tags, descriptions, and characteristics.
- **Budget Fit (25 pts)**:
  - Midpoint between `budget_min` and `budget_max` $\rightarrow 100\%$ ($25.0$ pts).
  - Midpoint below `budget_min` (Affordable saving) $\rightarrow \max(0.75, 1.0 - \Delta_{\text{min}} \times 0.25) \times 25$.
  - Midpoint above `budget_max` (Slight stretch within tolerance) $\rightarrow \max(0.40, 1.0 - \Delta_{\text{max}} \times 1.5) \times 25$.
- **Occasion & Relationship Relevance (20 pts)**: Intimacy calibration (Best Friend / Partner / Sibling vs. Colleague / Teacher) + event formality.
- **Stated Purpose Match (15 pts)**:
  - If user selected *Useful / Practical* $\rightarrow$ scaled by `practical_usefulness` ($1–10$).
  - If user selected *Sentimental / Memorable* $\rightarrow$ scaled by `sentimental_value` ($1–10$).
  - If user selected *Creative* $\rightarrow$ scaled by artisanal/DIY attributes.
- **Personalization Potential (10 pts)**: Custom engraving, monogramming, dedicated photo plates ($10.0$ pts) vs. standard off-the-shelf goods ($3.0–4.0$ pts).

---

## 6. Interactive Feedback & Adaptation Loop

When a user rejects an option using the UI feedback controls:
1. **"Too expensive"**: Tightens `budget_max` to $90\%$ of the rejected item's minimum cost.
2. **"Already owns it"**: Appends item name to `already_owned` list.
3. **"Try a different category"**: Adds the rejected item's category to `disliked_items`.
4. **"More practical"**: Injects "Practical" and "Useful" into preferences, increasing utility weight.
5. **"More creative"**: Excludes generic candidate, prioritizes artistic and craft gifts.
6. **"Not my style" / "Too generic"**: Eliminates the candidate and ensures the next selection comes from an alternative product category.

---

## 7. Dual Reasoning Modes (Gemini + Deterministic Fallback)

The agent operates across two modes:

### Mode 1: Gemini AI Reasoning (`gemini-2.5-flash`)
- **Activated when**: `GEMINI_API_KEY` is set in `.env` or system environment.
- **Functions performed**:
  - Creative candidate synthesis adhering to strict Pydantic JSON schemas.
  - Natural language feedback intent analysis.
  - Nuanced comparison rationale generation contrasting top pick with alternatives.

### Mode 2: Deterministic Fallback Engine
- **Activated when**: `GEMINI_API_KEY` is missing, blank, or experiencing network/quota limits.
- **Functions performed**:
  - Uses the curated `CATALOG_ITEMS` database spanning Indian market products (`₹200–₹35,000+`).
  - Employs heuristic keyword matching, category diversity enforcement, and transparent deterministic scoring.
  - Zero external API dependencies; 100% reliable for demos, viva evaluations, and offline environments.

---

## 8. Project Structure

```
Agent - 2/
├── app.py                      # FastAPI server & route handlers
├── requirements.txt            # Pinned dependencies
├── Procfile                    # Render deployment start command
├── render.yaml                 # Infrastructure as Code specification
├── .gitignore                  # Git exclusions (PDFs, .env, __pycache__)
├── .env.example                # Configuration template
├── README.md                   # System documentation & Viva guide
├── agent/
│   ├── __init__.py             # Agent exports
│   ├── state.py                # TypedDict GiftAgentState & Pydantic schemas
│   ├── catalog.py              # 30+ Indian market gift catalogue templates
│   ├── candidate_generator.py  # Gemini & deterministic candidate generator
│   ├── constraint_filter.py    # Hard constraint separation & filtering
│   ├── scoring_engine.py       # Deterministic 100-point scoring algorithm
│   ├── decision_reviewer.py    # Bounded quality & diversity review node
│   ├── graph.py                # LangGraph StateGraph definitions
│   └── llm_service.py          # Google Gemini integration via LangChain
├── services/
│   ├── __init__.py
│   └── report_service.py       # Professional ReportLab PDF generation
├── templates/
│   └── index.html              # Cream & lavender responsive web interface
├── static/
│   ├── style.css               # Luxury CSS typography, gauges & animations
│   └── script.js               # Client API interactions & feedback handlers
└── tests/
    ├── __init__.py
    ├── test_scoring.py          # Tests for weights and component formulas
    ├── test_constraints.py      # Tests for hard budget and exclusion rules
    ├── test_feedback.py         # Tests for adaptive rejection handling
    ├── test_agent_workflow.py   # Tests for LangGraph execution & review bounds
    └── test_api.py              # Tests for FastAPI endpoints & PDF streaming
```

---

## 9. Local Setup & Installation

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Git

### Steps
1. Navigate to Geetha's Agent 2 directory:
   ```bash
   cd "e:\Chaitanyaa\Geethuu\Agent - 2"
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. Install pinned dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (Optional for Gemini):
   ```bash
   copy .env.example .env
   ```
   Add your `GEMINI_API_KEY` in `.env` if desired. If left blank, the app runs in **Deterministic Fallback Mode** with complete functionality!

5. Start the web application:
   ```bash
   python app.py
   ```
   Or with Uvicorn:
   ```bash
   uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```

6. Open your browser and navigate to:
   `http://localhost:8000`

---

## 10. Running Automated Tests

Run the full pytest test suite:

```bash
pytest -v
```

### Test Coverage Highlights:
- **`test_scoring.py`**: Validates 30/25/20/15/10 weight normalization, under-budget rewards, and descending rank order.
- **`test_constraints.py`**: Verifies strict rejection for budget violations, excluded items, and already-owned goods.
- **`test_feedback.py`**: Verifies that feedback reduces budgets, updates exclusions, and guarantees non-repetition of rejected gifts.
- **`test_agent_workflow.py`**: Tests complete LangGraph state transitions and enforces the $\le 3$ regeneration attempt limit.
- **`test_api.py`**: Validates all FastAPI endpoints (`/`, `/health`, `/workflow`, `/recommend`, `/recommend/{id}`, `/report`).

---

## 11. Deployment on Render

This project is pre-configured for one-click deployment on [Render](https://render.com).

### Deployment Configuration
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- **Configuration Files**: `Procfile` and `render.yaml` are included.

### Setting Environment Variables on Render
1. Create a new **Web Service** pointing to your repository.
2. Under **Environment Variables**, configure:
   - `PYTHON_VERSION`: `3.12.10`
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API Key.
   - `GEMINI_MODEL`: `gemini-2.5-flash`
3. Click **Deploy**. The service will automatically bind to `$PORT` and launch.

---

## 12. Input / Output Examples

### Example 1: Birthday Gift for Best Friend
**Input**:
- Occasion: Birthday
- Recipient: Best friend
- Budget Range: ₹500 – ₹1,500
- Interests: Photography, Music
- Preferences: Useful, Memorable, Sentimental
- Avoid: Generic Mugs, Clothes

**Output**:
- **Selected Top Match**: *Customized Acrylic Music Plaque with Scannable Audio Code*
- **Match Score**: $92.5 / 100$
- **Estimated Budget Range**: ₹500 – ₹850 (Within Budget)
- **Component Breakdown**: Interest: $30.0/30$, Budget: $25.0/25$, Relevance: $19.0/20$, Purpose: $13.5/15$, Personalization: $10.0/10$
- **Alternative 1**: *Personalized Wooden Memory Album & Photo Journal* (Score: $91.0/100$)
- **Alternative 2**: *Clip-On Optical Smartphone Camera Lens Kit* (Score: $88.8/100$)
- **Trade-off Contrast**: The acrylic plaque provides immediate emotional connection and custom audio interaction, whereas the camera lens kit offers higher technical utility at the cost of less personal sentiment.

---

## 13. Viva Voce Questions & Answers

### Q1: What makes this an AI Agent rather than a standard chatbot or static recommender?
**Answer**: A chatbot generates unstructured text directly from a prompt without verifying constraints or tracking state. The Gift Decision Agent uses **LangGraph** to execute a typed, multi-stage state graph with conditional routing. It enforces deterministic hard constraints *before* scoring, calculates reproducible mathematical scores, audits recommendations through a Decision Reviewer, and programmatically adapts its internal state based on interactive feedback.

### Q2: Why separate Hard Constraints from Soft Preferences?
**Answer**: If all constraints are treated as soft preferences in a single weighted score, an expensive gift exceeding the user's budget could still "win" simply by having high sentimental points. Separating them ensures that budget ceilings, already-owned items, and user exclusions are absolute gates that disqualify non-compliant items before scoring begins.

### Q3: How is the scoring formula structured? Can the weights be changed?
**Answer**: The formula evaluates candidates on a normalized 100-point scale:
- Interest Match: $30\%$
- Budget Fit: $25\%$
- Occasion & Relationship Relevance: $20\%$
- Stated Purpose Match: $15\%$
- Personalization Potential: $10\%$
Weights are defined centrally in `agent/scoring_engine.py` in the `SCORING_WEIGHTS` dictionary, allowing administrators to recalibrate priorities without altering the core algorithm.

### Q4: How does the agent prevent infinite loops if candidates continually fail review?
**Answer**: The LangGraph state tracks `generation_attempts`. The conditional edges in `route_after_filter` and `route_after_review` check whether `generation_attempts < 3`. If the ceiling of 3 attempts is reached, the system halts regeneration and presents the closest viable candidate with transparent warning notes in the final report.

### Q5: How does the application handle situations where the Gemini API is offline or quota-limited?
**Answer**: The agent implements an automatic **Deterministic Fallback Engine**. The `LLMService` detects missing or invalid keys and network timeouts, instantly redirecting candidate generation to a curated 30+ item Indian market catalogue. Scoring and review proceed purely through Python logic, ensuring uninterrupted functionality.

### Q6: How does the agent adapt when a user rejects a recommendation?
**Answer**: The `/recommend/{session_id}/feedback` endpoint invokes a dedicated feedback graph:
1. It analyzes the rejection reason.
2. It permanently adds the rejected gift to `rejected_gifts` to prevent repetition.
3. If the reason was "Too expensive", it lowers the budget ceiling.
4. If "Try a different category", it bans that category.
5. It regenerates candidates and re-scores them to provide a fresh, contextually shifted recommendation.

---

## 14. Known Limitations & Disclaimers

1. **Market Price Estimates**: All price ranges (in INR ₹) are estimated standard retail brackets. The system does not scrape live real-time inventory from e-commerce sites without explicit external merchant API integrations. Users should verify live prices before purchase.
2. **In-Memory Session Persistence**: Active sessions are cached in server RAM for quick response times and reset upon server restart.
3. **No Subjective Guarantee**: Recommendations are presented as the mathematically and contextually best-supported matches based on the supplied criteria, not guaranteed personal reactions.
