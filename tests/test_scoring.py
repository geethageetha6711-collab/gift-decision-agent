"""
Unit tests for the Deterministic Scoring Engine.
Validates weight configuration, normalized 100-point formula, component scores,
and trade-off identification.
"""

import pytest
from agent.scoring_engine import score_candidate, SCORING_WEIGHTS, score_and_rank_gifts


def test_scoring_weights_sum_to_100():
    total_weights = sum(SCORING_WEIGHTS.values())
    assert total_weights == 100.0
    assert SCORING_WEIGHTS["interest_match"] == 30.0
    assert SCORING_WEIGHTS["budget_fit"] == 25.0
    assert SCORING_WEIGHTS["relevance"] == 20.0
    assert SCORING_WEIGHTS["purpose_match"] == 15.0
    assert SCORING_WEIGHTS["personalization"] == 10.0


def test_score_candidate_within_budget_and_perfect_interests():
    candidate = {
        "gift_name": "Personalized Wooden Memory Album",
        "gift_category": "Personalized Keepsakes",
        "estimated_cost_min": 600.0,
        "estimated_cost_max": 900.0,
        "description": "Scrapbook album for photography lovers.",
        "satisfied_interests": ["Photography"],
        "satisfied_preferences": ["Sentimental", "Memorable"],
        "personalization_possibilities": "Laser engraved cover",
        "practical_usefulness": 6,
        "sentimental_value": 10,
        "potential_drawbacks": "Requires printing photos",
        "price_confidence_indicator": "High (standard market estimate)"
    }

    state = {
        "budget_min": 500.0,
        "budget_max": 1500.0,
        "interests": ["Photography"],
        "preferences": ["Sentimental", "Memorable"],
        "occasion": "Birthday",
        "recipient": "Best friend",
        "relationship": "Close"
    }

    scored = score_candidate(candidate, state)
    assert 0.0 <= scored["total_score"] <= 100.0
    assert scored["total_score"] >= 85.0  # High score for perfect match

    breakdown = scored["score_breakdown"]
    assert breakdown["interest_match_score"] == 30.0
    assert breakdown["budget_fit_score"] == 25.0
    assert breakdown["relevance_score"] >= 18.0
    assert breakdown["personalization_score"] == 10.0
    assert len(scored["positive_factors"]) > 0


def test_score_candidate_under_budget():
    candidate = {
        "gift_name": "Custom Spotify Song Keychain",
        "gift_category": "Personalized Keepsakes",
        "estimated_cost_min": 250.0,
        "estimated_cost_max": 350.0,
        "description": "Small acrylic keychain",
        "satisfied_interests": ["Music"],
        "satisfied_preferences": ["Sentimental"],
        "personalization_possibilities": "Song code and photo",
        "practical_usefulness": 4,
        "sentimental_value": 8
    }

    state = {
        "budget_min": 800.0,
        "budget_max": 2000.0,
        "interests": ["Music"],
        "preferences": ["Sentimental"],
        "occasion": "Farewell",
        "recipient": "Friend"
    }

    scored = score_candidate(candidate, state)
    # Under budget should still get a good score, but slight adjustment compared to ideal budget target
    assert scored["score_breakdown"]["budget_fit_score"] >= 18.0
    assert any("under minimum" in f.lower() or "saves" in f.lower() for f in scored["positive_factors"])


def test_ranking_sorts_descending():
    c1 = {
        "gift_name": "Low Match Item",
        "gift_category": "Other",
        "estimated_cost_min": 100.0,
        "estimated_cost_max": 200.0,
        "description": "Generic item",
        "satisfied_interests": [],
        "satisfied_preferences": [],
        "personalization_possibilities": "",
        "practical_usefulness": 5,
        "sentimental_value": 5
    }
    c2 = {
        "gift_name": "High Match Item",
        "gift_category": "Tech & Gadgets",
        "estimated_cost_min": 1000.0,
        "estimated_cost_max": 1500.0,
        "description": "Amazing tech gadget for tech lover",
        "satisfied_interests": ["Tech"],
        "satisfied_preferences": ["Useful"],
        "personalization_possibilities": "Custom engraving",
        "practical_usefulness": 9,
        "sentimental_value": 7
    }

    state = {
        "filtered_candidates": [c1, c2],
        "budget_min": 800.0,
        "budget_max": 2000.0,
        "interests": ["Tech"],
        "preferences": ["Useful"],
        "occasion": "Birthday",
        "recipient": "Partner"
    }

    result = score_and_rank_gifts(state)
    ranked = result["ranked_gifts"]
    assert len(ranked) == 2
    assert ranked[0]["gift_name"] == "High Match Item"
    assert ranked[0]["total_score"] > ranked[1]["total_score"]
    assert result["selected_gift"]["gift_name"] == "High Match Item"
