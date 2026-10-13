"""
Decision Reviewer Node.
Critiques the proposed top recommendation against budget constraints, category diversity,
exclusion compliance, interest representation, and transparent qualification.
Triggers bounded regeneration (up to 3 attempts) if criteria fail.
"""

from typing import Dict, Any, List
from agent.llm_service import llm_service


def review_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the quality, consistency, and constraints of the top candidate and alternatives.
    """
    selected = state.get("selected_gift")
    alternatives = state.get("alternatives", [])
    budget_max = float(state.get("budget_max", 100000.0))
    disliked = [d.lower() for d in state.get("disliked_items", []) if d]
    owned = [a.lower() for a in state.get("already_owned", []) if a]
    attempts = state.get("generation_attempts", 1)

    review_notes: List[str] = list(state.get("review_notes", []))
    warning_messages: List[str] = list(state.get("warning_messages", []))
    needs_regeneration = False

    if not selected:
        review_notes.append("Critical: No candidates survived to selection stage.")
        needs_regeneration = True if attempts < 3 else False
        return {
            "review_notes": review_notes,
            "needs_regeneration": needs_regeneration,
            "status": "review_failed_no_candidate"
        }

    # 1. Budget Verification
    cost_min = float(selected.get("estimated_cost_min", 0.0))
    if cost_min > budget_max:
        review_notes.append(f"Budget Failure: Selected gift min cost (₹{int(cost_min):,}) exceeds max budget ₹{int(budget_max):,}.")
        needs_regeneration = True

    # 2. Exclusion & Ownership Verification
    sel_name = selected.get("gift_name", "").lower()
    sel_cat = selected.get("gift_category", "").lower()
    for dis in disliked:
        if dis in sel_name or dis in sel_cat:
            review_notes.append(f"Exclusion Failure: Selected gift contains excluded element '{dis}'.")
            needs_regeneration = True
    for o in owned:
        if o in sel_name:
            review_notes.append(f"Ownership Failure: Recipient already owns '{o}'.")
            needs_regeneration = True

    # 3. Category Diversity Check
    categories = [selected.get("gift_category")] + [a.get("gift_category") for a in alternatives if a]
    unique_categories = set(categories)
    if len(categories) >= 3 and len(unique_categories) < 2:
        review_notes.append("Diversity Warning: Top candidate and alternatives share identical categories.")
        if attempts < 2:
            needs_regeneration = True

    # 4. Interest Representation Check
    score_breakdown = selected.get("score_breakdown", {})
    interest_score = score_breakdown.get("interest_match_score", 0.0)
    if interest_score < 10.0 and state.get("interests"):
        review_notes.append("Relevance Warning: Selected gift exhibits weak alignment with primary listed hobbies.")

    # 5. Price & Qualification Disclaimer
    if not selected.get("verification_status"):
        selected["verification_status"] = "Unverified market estimate - check local retail/e-commerce before purchase"

    # Enforce attempt bound (maximum 3 attempts)
    if attempts >= 3 and needs_regeneration:
        review_notes.append(f"Regeneration attempt ceiling reached ({attempts}/3). Proceeding with best viable match.")
        needs_regeneration = False

    if not needs_regeneration:
        review_notes.append("Decision Reviewer: Quality benchmarks satisfied. Proceeding to final synthesis.")

    return {
        "review_notes": review_notes,
        "needs_regeneration": needs_regeneration,
        "warning_messages": warning_messages,
        "status": "review_completed"
    }


def synthesize_final_recommendation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the final report and decision explanation.
    Uses Gemini when available, or formats a rich deterministic decision report.
    """
    selected = state.get("selected_gift")
    alternatives = state.get("alternatives", [])
    user_occasion = state.get("occasion", "")
    user_recipient = state.get("recipient", "")

    if not selected:
        explanation = (
            f"No suitable gift candidate was found within the requested parameters. "
            f"The maximum budget of ₹{state.get('budget_max', 0):,} or active category exclusions "
            f"may be too restrictive. Please consider adjusting the budget or removing exclusion filters."
        )
        report = {
            "success": False,
            "session_id": state.get("session_id"),
            "selected_gift": None,
            "alternatives": [],
            "decision_explanation": explanation,
            "review_notes": state.get("review_notes", []),
            "warning_messages": state.get("warning_messages", []),
            "mode": state.get("mode", "deterministic_fallback")
        }
        return {
            "decision_explanation": explanation,
            "final_report": report,
            "status": "completed_no_match"
        }

    # Attempt Gemini explanation
    explanation = None
    if state.get("mode") == "gemini" and llm_service.is_available():
        explanation = llm_service.explain_decision(selected, alternatives, state)

    if not explanation:
        # High quality deterministic synthesis
        interests_str = ", ".join(state.get("interests", ["their interests"]))
        purposes_str = ", ".join(state.get("preferences", ["everyday gifting"]))
        
        reasons_bullet = "\n".join([f"• {f}" for f in selected.get("positive_factors", [])])
        tradeoffs_bullet = "\n".join([f"• {t}" for t in selected.get("trade_offs", [])])
        
        alt_comparisons = ""
        for a in alternatives[:3]:
            alt_comparisons += (
                f"\n• **{a.get('gift_name')}** ({a.get('gift_category')}, ₹{int(a.get('estimated_cost_min',0))}-₹{int(a.get('estimated_cost_max',0))} | Score: {a.get('total_score',0)}/100): "
                f"{a.get('trade_offs', ['Alternative option'])[0]}."
            )

        explanation = (
            f"### Decision Rationale for {user_recipient} ({user_occasion})\n\n"
            f"**{selected.get('gift_name')}** was selected as the optimal recommendation with a match score of "
            f"**{selected.get('total_score')}/100**, achieving the highest overall balance across your budget, "
            f"the recipient's passion for {interests_str}, and your goal of gifting something {purposes_str}.\n\n"
            f"**Key Advantages:**\n{reasons_bullet}\n\n"
            f"**Trade-offs & Considerations:**\n{tradeoffs_bullet}\n\n"
            f"**Comparison with Viable Alternatives:**{alt_comparisons}\n\n"
            f"**Suggested Personalization Touch:**\n"
            f"{selected.get('personalization_possibilities', 'Include a personalized handwritten card with meaningful memories.')}\n\n"
            f"*Note: Estimated market price range is ₹{int(selected.get('estimated_cost_min',0)):,} to ₹{int(selected.get('estimated_cost_max',0)):,}. "
            f"Check current retail listings before finalizing purchase.*"
        )

    final_report = {
        "success": True,
        "session_id": state.get("session_id"),
        "occasion": user_occasion,
        "recipient": user_recipient,
        "relationship": state.get("relationship", "Close"),
        "budget_range": f"₹{int(state.get('budget_min', 0)):,} – ₹{int(state.get('budget_max', 0)):,}",
        "interests": state.get("interests", []),
        "preferences": state.get("preferences", []),
        "selected_gift": selected,
        "alternatives": alternatives,
        "decision_explanation": explanation,
        "review_notes": state.get("review_notes", []),
        "warning_messages": state.get("warning_messages", []),
        "mode": state.get("mode", "deterministic_fallback"),
        "generation_attempts": state.get("generation_attempts", 1),
        "feedback_history": state.get("feedback_history", [])
    }

    return {
        "decision_explanation": explanation,
        "final_report": final_report,
        "status": "completed"
    }
