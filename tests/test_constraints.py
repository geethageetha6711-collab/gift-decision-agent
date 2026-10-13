"""
Unit tests for the Constraint Filter Node.
Validates hard budget limits, explicit category exclusions, already owned items,
and required gift types.
"""

import pytest
from agent.constraint_filter import filter_constraints


def test_hard_budget_violation_rejection():
    candidate_expensive = {
        "gift_name": "Luxury Designer Watch",
        "gift_category": "Fashion",
        "estimated_cost_min": 5000.0,
        "estimated_cost_max": 8000.0,
        "description": "Premium watch",
        "personalization_possibilities": ""
    }
    candidate_affordable = {
        "gift_name": "Classic Leather Wallet",
        "gift_category": "Accessories",
        "estimated_cost_min": 700.0,
        "estimated_cost_max": 1000.0,
        "description": "Everyday wallet",
        "personalization_possibilities": "Monogram"
    }

    state = {
        "candidate_gifts": [candidate_expensive, candidate_affordable],
        "budget_max": 1500.0,
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "No preference"
    }

    result = filter_constraints(state)
    filtered = result["filtered_candidates"]
    rejected = result["rejected_candidates"]

    assert len(filtered) == 1
    assert filtered[0]["gift_name"] == "Classic Leather Wallet"
    assert len(rejected) == 1
    assert rejected[0]["candidate"]["gift_name"] == "Luxury Designer Watch"
    assert "exceeds your maximum budget" in rejected[0]["reason"]


def test_exclusion_rule_rejection():
    c1 = {
        "gift_name": "Ceramic Coffee Mug with Lid",
        "gift_category": "Home & Living",
        "estimated_cost_min": 400.0,
        "estimated_cost_max": 600.0,
        "description": "Warm coffee mug"
    }
    c2 = {
        "gift_name": "Scented Soy Candle",
        "gift_category": "Home & Living",
        "estimated_cost_min": 500.0,
        "estimated_cost_max": 700.0,
        "description": "Relaxing candle"
    }

    state = {
        "candidate_gifts": [c1, c2],
        "budget_max": 1000.0,
        "disliked_items": ["Mug", "Cup"],
        "already_owned": [],
        "gift_type": "No preference"
    }

    result = filter_constraints(state)
    assert len(result["filtered_candidates"]) == 1
    assert result["filtered_candidates"][0]["gift_name"] == "Scented Soy Candle"
    assert any("exclusion rule" in r["reason"].lower() for r in result["rejected_candidates"])


def test_already_owned_rejection():
    c1 = {
        "gift_name": "Kindle Paperwhite E-Reader",
        "gift_category": "Tech & Gadgets",
        "estimated_cost_min": 9000.0,
        "estimated_cost_max": 12000.0,
        "description": "Digital book reader"
    }

    state = {
        "candidate_gifts": [c1],
        "budget_max": 15000.0,
        "disliked_items": [],
        "already_owned": ["Kindle"],
        "gift_type": "No preference"
    }

    result = filter_constraints(state)
    assert len(result["filtered_candidates"]) == 0
    assert len(result["rejected_candidates"]) == 1
    assert "already owns" in result["rejected_candidates"][0]["reason"].lower()


def test_mandatory_gift_type_enforcement():
    c_physical = {
        "gift_name": "Leather Messenger Bag",
        "gift_category": "Fashion",
        "estimated_cost_min": 1500.0,
        "estimated_cost_max": 2500.0,
        "description": "Standard physical leather bag",
        "personalization_possibilities": ""
    }
    c_exp = {
        "gift_name": "Pottery Wheel Workshop Pass",
        "gift_category": "Experiences & Dining",
        "estimated_cost_min": 2000.0,
        "estimated_cost_max": 3000.0,
        "description": "2-hour pottery studio experience pass",
        "personalization_possibilities": "Voucher card"
    }

    state = {
        "candidate_gifts": [c_physical, c_exp],
        "budget_max": 4000.0,
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "Experience"
    }

    result = filter_constraints(state)
    assert len(result["filtered_candidates"]) == 1
    assert result["filtered_candidates"][0]["gift_name"] == "Pottery Wheel Workshop Pass"
