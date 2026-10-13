"""
Unit tests for the Interactive Feedback Adaptation Loop.
Tests rejection reason parsing, constraint updates, category exclusions,
and non-repetition of rejected items.
"""

import pytest
from agent.graph import feedback_analyzer, preference_updater
from agent.candidate_generator import generate_candidate_gifts


def test_feedback_too_expensive_reduces_budget():
    selected = {
        "gift_name": "Premium Gimbal Stabilizer",
        "gift_category": "Tech & Gadgets",
        "estimated_cost_min": 5000.0,
        "estimated_cost_max": 7000.0
    }
    state = {
        "budget_max": 6000.0,
        "selected_gift": selected,
        "rejected_gifts": [],
        "disliked_items": [],
        "already_owned": [],
        "preferences": [],
        "feedback_history": [{"reason": "Too expensive", "custom_feedback": ""}]
    }

    updated = preference_updater(state)
    assert updated["budget_max"] < 5000.0  # Budget reduced below the rejected item's min price
    assert len(updated["rejected_gifts"]) == 1
    assert updated["rejected_gifts"][0]["gift_name"] == "Premium Gimbal Stabilizer"


def test_feedback_already_owns_adds_to_owned():
    selected = {
        "gift_name": "Kindle Paperwhite",
        "gift_category": "Tech & Gadgets"
    }
    state = {
        "budget_max": 10000.0,
        "selected_gift": selected,
        "rejected_gifts": [],
        "disliked_items": [],
        "already_owned": [],
        "preferences": [],
        "feedback_history": [{"reason": "Already owns it", "custom_feedback": ""}]
    }

    updated = preference_updater(state)
    assert "Kindle Paperwhite" in updated["already_owned"]


def test_feedback_different_category_adds_to_disliked():
    selected = {
        "gift_name": "Watercolor Painting Kit",
        "gift_category": "Art & Creative"
    }
    state = {
        "budget_max": 2000.0,
        "selected_gift": selected,
        "rejected_gifts": [],
        "disliked_items": [],
        "already_owned": [],
        "preferences": [],
        "feedback_history": [{"reason": "Try a different category", "custom_feedback": ""}]
    }

    updated = preference_updater(state)
    assert "Art & Creative" in updated["disliked_items"]


def test_feedback_candidate_regeneration_excludes_rejected():
    rejected_gift = {
        "gift_name": "Personalized Wooden Memory Album & Photo Journal",
        "gift_category": "Personalized Keepsakes"
    }
    state = {
        "occasion": "Birthday",
        "recipient": "Best friend",
        "relationship": "Close",
        "budget_min": 500.0,
        "budget_max": 1500.0,
        "interests": ["photography", "music"],
        "preferences": ["Useful", "Creative"],
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "No preference",
        "rejected_gifts": [rejected_gift],
        "generation_attempts": 0
    }

    res = generate_candidate_gifts(state)
    candidate_names = [c["gift_name"] for c in res["candidate_gifts"]]
    assert "Personalized Wooden Memory Album & Photo Journal" not in candidate_names
