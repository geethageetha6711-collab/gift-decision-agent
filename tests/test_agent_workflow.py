"""
Integration tests for the LangGraph Agent Workflows.
Tests state transitions, conditional edges, review loops, bounded regeneration,
and fallback execution.
"""

import pytest
from agent.graph import create_gift_agent_graph, create_feedback_graph, preference_validator
from agent.decision_reviewer import review_decision


def test_preference_validator_normalizes_data():
    raw_state = {
        "budget_min": -50.0,
        "budget_max": 20.0,
        "interests": ["  Tech ", ""],
        "preferences": [" Useful "],
        "disliked_items": [],
        "already_owned": []
    }
    validated = preference_validator(raw_state)
    assert validated["budget_min"] >= 0.0
    assert validated["budget_max"] >= validated["budget_min"]
    assert validated["interests"] == ["Tech"]
    assert validated["preferences"] == ["Useful"]


def test_main_workflow_end_to_end_execution():
    graph = create_gift_agent_graph()

    input_state = {
        "session_id": "test-session-001",
        "occasion": "Birthday",
        "recipient": "Best friend",
        "relationship": "Close",
        "budget_min": 500.0,
        "budget_max": 2000.0,
        "interests": ["Music", "Reading"],
        "preferences": ["Useful", "Memorable"],
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "No preference",
        "preferred_style": "",
        "age_range": "20s",
        "deadline": "",
        "optional_notes": ""
    }

    result = graph.invoke(input_state)

    assert result["status"] == "completed"
    assert result["selected_gift"] is not None
    assert "gift_name" in result["selected_gift"]
    assert result["selected_gift"]["total_score"] > 0
    assert len(result["alternatives"]) >= 1
    assert "final_report" in result
    assert result["final_report"]["success"] is True
    assert result["generation_attempts"] >= 1
    assert result["generation_attempts"] <= 3


def test_decision_reviewer_bounded_attempts():
    # Simulate a failing state with attempts = 3
    selected_over_budget = {
        "gift_name": "Ultra Expensive Yacht",
        "gift_category": "Luxury",
        "estimated_cost_min": 500000.0,
        "estimated_cost_max": 1000000.0,
        "total_score": 50.0,
        "score_breakdown": {"interest_match_score": 15.0}
    }
    failing_state = {
        "selected_gift": selected_over_budget,
        "alternatives": [],
        "budget_max": 1000.0,
        "disliked_items": [],
        "already_owned": [],
        "generation_attempts": 3,
        "review_notes": []
    }

    review_res = review_decision(failing_state)
    # Even though budget failed, attempt ceiling of 3 must prevent infinite loop!
    assert review_res["needs_regeneration"] is False
    assert any("ceiling reached" in note.lower() for note in review_res["review_notes"])


def test_feedback_workflow_end_to_end():
    main_graph = create_gift_agent_graph()
    feedback_graph = create_feedback_graph()

    state = {
        "session_id": "test-feedback-flow",
        "occasion": "Graduation",
        "recipient": "Sibling",
        "relationship": "Close",
        "budget_min": 500.0,
        "budget_max": 2000.0,
        "interests": ["Coffee", "Art"],
        "preferences": ["Creative"],
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "No preference",
        "preferred_style": "",
        "age_range": "",
        "deadline": "",
        "optional_notes": ""
    }

    # First recommendation run
    first_res = main_graph.invoke(state)
    first_gift_name = first_res["selected_gift"]["gift_name"]
    assert first_gift_name is not None

    # Inject user feedback rejecting the first option as "Not my style"
    first_res["feedback_history"] = [{
        "reason": "Not my style",
        "custom_feedback": "Prefer something related to manual brewing",
        "rejected_gift_name": first_gift_name
    }]

    # Feedback run
    updated_res = feedback_graph.invoke(first_res)
    assert updated_res["selected_gift"] is not None
    # Rejection constraint must ensure different candidate or updated focus
    assert updated_res["selected_gift"]["gift_name"] != first_gift_name
