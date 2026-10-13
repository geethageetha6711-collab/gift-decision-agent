"""
LangGraph Workflows for the Gift Decision Agent.
Implements the main decision graph and interactive feedback graph with real state transitions
and conditional routing edges.
"""

from typing import Dict, Any, Literal
import copy
from langgraph.graph import StateGraph, START, END

from agent.state import GiftAgentState
from agent.candidate_generator import generate_candidate_gifts
from agent.constraint_filter import filter_constraints
from agent.scoring_engine import score_and_rank_gifts
from agent.decision_reviewer import review_decision, synthesize_final_recommendation
from agent.llm_service import llm_service


# ---------------- Preference Validator Node ----------------
def preference_validator(state: GiftAgentState) -> Dict[str, Any]:
    """
    Validates user input values, normalizes budget boundaries,
    and initializes execution defaults.
    """
    budget_min = float(state.get("budget_min", 500.0))
    budget_max = float(state.get("budget_max", 5000.0))
    if budget_max < budget_min:
        budget_max = budget_min * 1.5

    clean_interests = [i.strip() for i in state.get("interests", []) if i.strip()]
    if not clean_interests:
        clean_interests = ["General Lifestyle"]

    clean_prefs = [p.strip() for p in state.get("preferences", []) if p.strip()]
    clean_disliked = [d.strip() for d in state.get("disliked_items", []) if d.strip()]
    clean_owned = [o.strip() for o in state.get("already_owned", []) if o.strip()]

    return {
        "budget_min": max(0.0, budget_min),
        "budget_max": max(100.0, budget_max),
        "interests": clean_interests,
        "preferences": clean_prefs,
        "disliked_items": clean_disliked,
        "already_owned": clean_owned,
        "generation_attempts": state.get("generation_attempts", 0),
        "warning_messages": state.get("warning_messages", []),
        "review_notes": state.get("review_notes", []),
        "rejected_gifts": state.get("rejected_gifts", []),
        "feedback_history": state.get("feedback_history", []),
        "status": "preferences_validated"
    }


# ---------------- Feedback Analyzer & Preference Updater Nodes ----------------
def feedback_analyzer(state: GiftAgentState) -> Dict[str, Any]:
    """
    Analyzes user rejection reason and notes to understand required adaptation.
    """
    history = list(state.get("feedback_history", []))
    latest_feedback = history[-1] if history else {"reason": "Not specified", "custom_feedback": ""}
    reason = latest_feedback.get("reason", "")
    custom_feedback = latest_feedback.get("custom_feedback", "")
    rejected_gift = state.get("selected_gift")

    analysis_result = None
    if state.get("mode") == "gemini" and llm_service.is_available():
        analysis_result = llm_service.analyze_feedback(reason, custom_feedback, rejected_gift, state)

    return {
        "status": "feedback_analyzed",
        "updated_preferences": analysis_result.get("preference_adjustments", {}) if analysis_result else {}
    }


def preference_updater(state: GiftAgentState) -> Dict[str, Any]:
    """
    Updates session constraints and preferences based on feedback analysis.
    Excludes rejected candidates, adapts budget ceilings, and adjusts desired purposes.
    """
    history = list(state.get("feedback_history", []))
    latest_feedback = history[-1] if history else {"reason": "", "custom_feedback": ""}
    reason = latest_feedback.get("reason", "").lower()
    custom = latest_feedback.get("custom_feedback", "").lower()
    
    selected = state.get("selected_gift")
    rejected_gifts = list(state.get("rejected_gifts", []))
    disliked_items = list(state.get("disliked_items", []))
    already_owned = list(state.get("already_owned", []))
    preferences = list(state.get("preferences", []))
    budget_max = float(state.get("budget_max", 5000.0))

    if selected:
        rejected_gifts.append(selected)

    # Apply deterministic feedback adaptation rules
    if "too expensive" in reason or "expensive" in custom:
        if selected:
            # Reduce budget max to the rejected item's minimum cost or lower by 20%
            budget_max = max(300.0, float(selected.get("estimated_cost_min", budget_max)) * 0.9)
    
    if "already owns" in reason or "owns" in custom:
        if selected:
            already_owned.append(selected.get("gift_name"))

    if "category" in reason or "different category" in reason:
        if selected:
            cat = selected.get("gift_category")
            if cat and cat not in disliked_items:
                disliked_items.append(cat)

    if "practical" in reason or "more practical" in reason or "useful" in custom:
        if "Practical" not in preferences:
            preferences.append("Practical")
        if "Useful" not in preferences:
            preferences.append("Useful")

    if "sentimental" in reason or "more sentimental" in reason:
        if "Sentimental" not in preferences:
            preferences.append("Sentimental")
        if "Memorable" not in preferences:
            preferences.append("Memorable")

    if "creative" in reason or "more creative" in reason or "generic" in reason:
        if "Creative" not in preferences:
            preferences.append("Creative")
        if selected:
            disliked_items.append(selected.get("gift_name"))

    return {
        "budget_max": budget_max,
        "disliked_items": list(set(disliked_items)),
        "already_owned": list(set(already_owned)),
        "preferences": list(set(preferences)),
        "rejected_gifts": rejected_gifts,
        "generation_attempts": 0,  # Reset attempts for new feedback iteration
        "status": "preferences_updated"
    }


# ---------------- Conditional Routing Logic ----------------
def route_after_filter(state: GiftAgentState) -> Literal["regenerate", "score"]:
    """
    Routes back to candidate generation if too few valid options remain
    and maximum generation attempts (3) have not been exhausted.
    """
    needs_regen = state.get("needs_regeneration", False)
    attempts = state.get("generation_attempts", 1)
    if needs_regen and attempts < 3:
        return "regenerate"
    return "score"


def route_after_review(state: GiftAgentState) -> Literal["regenerate", "finalize"]:
    """
    Routes back to candidate generation if decision reviewer flags issues
    and attempts < 3. Otherwise routes to final recommendation synthesis.
    """
    needs_regen = state.get("needs_regeneration", False)
    attempts = state.get("generation_attempts", 1)
    if needs_regen and attempts < 3:
        return "regenerate"
    return "finalize"


# ---------------- Main Recommendation Graph ----------------
def create_gift_agent_graph():
    """
    Builds the main Gift Decision LangGraph workflow:
    START
    → preference_validator
    → candidate_generator
    → constraint_filter
    → [conditional: route_after_filter -> regenerate or score]
    → scoring_engine
    → decision_reviewer
    → [conditional: route_after_review -> regenerate or finalize]
    → final_recommendation
    → END
    """
    builder = StateGraph(GiftAgentState)

    builder.add_node("preference_validator", preference_validator)
    builder.add_node("candidate_generator", generate_candidate_gifts)
    builder.add_node("constraint_filter", filter_constraints)
    builder.add_node("scoring_engine", score_and_rank_gifts)
    builder.add_node("decision_reviewer", review_decision)
    builder.add_node("final_recommendation", synthesize_final_recommendation)

    builder.add_edge(START, "preference_validator")
    builder.add_edge("preference_validator", "candidate_generator")
    builder.add_edge("candidate_generator", "constraint_filter")

    builder.add_conditional_edges(
        "constraint_filter",
        route_after_filter,
        {
            "regenerate": "candidate_generator",
            "score": "scoring_engine"
        }
    )

    builder.add_edge("scoring_engine", "decision_reviewer")

    builder.add_conditional_edges(
        "decision_reviewer",
        route_after_review,
        {
            "regenerate": "candidate_generator",
            "finalize": "final_recommendation"
        }
    )

    builder.add_edge("final_recommendation", END)

    return builder.compile()


# ---------------- Interactive Feedback Graph ----------------
def create_feedback_graph():
    """
    Builds the adaptive Feedback LangGraph workflow:
    START
    → feedback_analyzer
    → preference_updater
    → candidate_regenerator
    → constraint_filter
    → scoring_engine
    → decision_reviewer
    → [conditional: route_after_review]
    → final_recommendation
    → END
    """
    builder = StateGraph(GiftAgentState)

    builder.add_node("feedback_analyzer", feedback_analyzer)
    builder.add_node("preference_updater", preference_updater)
    builder.add_node("candidate_regenerator", generate_candidate_gifts)
    builder.add_node("constraint_filter", filter_constraints)
    builder.add_node("scoring_engine", score_and_rank_gifts)
    builder.add_node("decision_reviewer", review_decision)
    builder.add_node("final_recommendation", synthesize_final_recommendation)

    builder.add_edge(START, "feedback_analyzer")
    builder.add_edge("feedback_analyzer", "preference_updater")
    builder.add_edge("preference_updater", "candidate_regenerator")
    builder.add_edge("candidate_regenerator", "constraint_filter")
    builder.add_edge("constraint_filter", "scoring_engine")
    builder.add_edge("scoring_engine", "decision_reviewer")

    builder.add_conditional_edges(
        "decision_reviewer",
        route_after_review,
        {
            "regenerate": "candidate_regenerator",
            "finalize": "final_recommendation"
        }
    )

    builder.add_edge("final_recommendation", END)

    return builder.compile()
