"""
Deterministic Gift Scoring Engine.
Calculates transparent, normalized 100-point scores with component breakdowns
based on interest match (30%), budget fit (25%), relevance (20%),
purpose match (15%), and personalization potential (10%).
"""

from typing import Dict, Any, List, Optional
import copy

SCORING_WEIGHTS: Dict[str, float] = {
    "interest_match": 30.0,
    "budget_fit": 25.0,
    "relevance": 20.0,
    "purpose_match": 15.0,
    "personalization": 10.0,
}


def score_candidate(candidate: Dict[str, Any], state: Dict[str, Any], weights: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Computes a transparent, multi-factor score out of 100 for a single candidate.
    """
    if weights is None:
        weights = SCORING_WEIGHTS

    scored = copy.deepcopy(candidate)
    user_interests = [i.lower().strip() for i in state.get("interests", []) if i.strip()]
    user_prefs = [p.lower().strip() for p in state.get("preferences", []) if p.strip()]
    budget_min = float(state.get("budget_min", 500.0))
    budget_max = float(state.get("budget_max", 5000.0))
    user_occasion = state.get("occasion", "").lower()
    user_recipient = state.get("recipient", "").lower()

    name = scored.get("gift_name", "").lower()
    category = scored.get("gift_category", "").lower()
    description = scored.get("description", "").lower()
    combined_text = f"{name} {category} {description}"

    cost_min = float(scored.get("estimated_cost_min", 0.0))
    cost_max = float(scored.get("estimated_cost_max", cost_min))
    cost_mid = (cost_min + cost_max) / 2.0

    positive_factors: List[str] = []
    trade_offs: List[str] = []

    # ---------------- 1. Interest Match (30%) ----------------
    matched_interests = 0
    for interest in user_interests:
        if (interest in combined_text or
            any(interest in s.lower() for s in scored.get("satisfied_interests", []))):
            matched_interests += 1

    if user_interests:
        interest_ratio = matched_interests / len(user_interests)
        if matched_interests > 0:
            interest_factor = min(1.0, 0.45 + (0.55 * interest_ratio))
            positive_factors.append(f"Direct match with {matched_interests} stated interest(s)")
        else:
            interest_factor = 0.35
            trade_offs.append("Only indirect correlation with primary listed hobbies")
    else:
        interest_factor = 0.70  # Neutral baseline if no interests given

    interest_score = round(interest_factor * weights["interest_match"], 1)

    # ---------------- 2. Budget Fit (25%) ----------------
    if budget_min <= cost_mid <= budget_max:
        budget_factor = 1.0
        positive_factors.append(f"Comfortably situated within your target range (₹{int(budget_min):,}–₹{int(budget_max):,})")
    elif cost_mid < budget_min:
        # Under budget: highly affordable, slight adjustment
        discount_ratio = (budget_min - cost_mid) / max(1.0, budget_min)
        budget_factor = max(0.75, 1.0 - (discount_ratio * 0.25))
        positive_factors.append(f"High value under minimum target (saves ₹{int(budget_min - cost_mid):,})")
    else:
        # Slight stretch above budget
        over_ratio = (cost_mid - budget_max) / max(1.0, budget_max)
        budget_factor = max(0.40, 1.0 - (over_ratio * 1.5))
        trade_offs.append(f"Estimated cost (₹{int(cost_mid):,}) stretches maximum budget threshold")

    budget_score = round(budget_factor * weights["budget_fit"], 1)

    # ---------------- 3. Occasion & Relationship Relevance (20%) ----------------
    relevance_points = 0.0

    # Occasion appropriateness
    if any(occ in user_occasion for occ in ["birthday", "anniversary", "wedding", "graduation"]):
        relevance_points += 0.50
    elif any(occ in user_occasion for occ in ["farewell", "thank you", "festival"]):
        relevance_points += 0.45
    else:
        relevance_points += 0.40

    # Relationship appropriateness
    if any(rel in user_recipient for rel in ["best friend", "partner", "sibling"]):
        relevance_points += 0.50
        positive_factors.append(f"Well-suited for close personal connection with {state.get('recipient')}")
    elif any(rel in user_recipient for rel in ["colleague", "teacher"]):
        # Verify it's not overly intimate
        if scored.get("practical_usefulness", 7) >= 7:
            relevance_points += 0.50
            positive_factors.append("Professional and thoughtful balance")
        else:
            relevance_points += 0.35
            trade_offs.append("Somewhat personal; verify appropriateness for workplace or formal gifting")
    else:
        relevance_points += 0.45

    relevance_factor = min(1.0, relevance_points)
    relevance_score = round(relevance_factor * weights["relevance"], 1)

    # ---------------- 4. Stated Gift Purpose Match (15%) ----------------
    practical_val = scored.get("practical_usefulness", 7) / 10.0
    sentimental_val = scored.get("sentimental_value", 7) / 10.0

    purpose_factor = 0.70  # Default neutral
    if any(p in user_prefs for p in ["useful", "practical"]):
        purpose_factor = practical_val
        if practical_val >= 0.8:
            positive_factors.append("Exceptional daily practical utility")
        else:
            trade_offs.append("More decorative or keepsake-oriented than high daily utility")
    elif any(p in user_prefs for p in ["sentimental", "memorable"]):
        purpose_factor = sentimental_val
        if sentimental_val >= 0.8:
            positive_factors.append("High sentimental and emotional keepsake resonance")
        else:
            trade_offs.append("More utilitarian; lower emotional keepsake depth")
    elif any(p in user_prefs for p in ["creative"]):
        if any(w in combined_text for w in ["art", "diy", "craft", "music", "photo", "creative"]):
            purpose_factor = 0.95
            positive_factors.append("Distinctive creative and artistic flair")
        else:
            purpose_factor = 0.65

    purpose_score = round(purpose_factor * weights["purpose_match"], 1)

    # ---------------- 5. Personalization Potential (10%) ----------------
    pers_text = scored.get("personalization_possibilities", "").strip()
    if pers_text and pers_text.lower() not in ["none", "none noted"]:
        pers_factor = 1.0
        positive_factors.append("Offers rich custom engraving or personal tailoring options")
    elif "personalized" in category or "personalized" in name:
        pers_factor = 0.90
    else:
        pers_factor = 0.40
        trade_offs.append("Standard off-the-shelf product with limited custom engraving")

    personalization_score = round(pers_factor * weights["personalization"], 1)

    # ---------------- Total Normalized Score ----------------
    total_score = round(interest_score + budget_score + relevance_score + purpose_score + personalization_score, 1)

    scored["total_score"] = total_score
    scored["score_breakdown"] = {
        "interest_match_score": interest_score,
        "budget_fit_score": budget_score,
        "relevance_score": relevance_score,
        "purpose_match_score": purpose_score,
        "personalization_score": personalization_score,
        "max_weights": weights
    }
    scored["positive_factors"] = positive_factors[:3]
    scored["trade_offs"] = trade_offs[:2] if trade_offs else ["Standard care or maintenance required"]
    
    # Uncertainty
    scored["cost_uncertainty"] = (
        "Low - consistent standard retail price"
        if scored.get("price_confidence_indicator", "").startswith("High")
        else "Moderate - subject to custom vendor variations"
    )

    return scored


def score_and_rank_gifts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main LangGraph node for Scoring and Ranking.
    Calculates deterministic multi-attribute scores for all filtered candidates,
    sorts them descending by score, and extracts top recommendation and alternatives.
    """
    candidates = state.get("filtered_candidates", [])
    if not candidates:
        # Fallback to candidate_gifts if filtering removed everything
        candidates = state.get("candidate_gifts", [])

    scored_list = [score_candidate(c, state) for c in candidates]

    # Sort descending by total_score
    scored_list.sort(key=lambda x: x["total_score"], reverse=True)

    selected_gift = scored_list[0] if scored_list else None
    alternatives = scored_list[1:4] if len(scored_list) > 1 else []

    scoring_breakdown = {
        "weights_used": SCORING_WEIGHTS,
        "top_score": selected_gift["total_score"] if selected_gift else 0.0,
        "candidate_count": len(scored_list)
    }

    return {
        "ranked_gifts": scored_list,
        "selected_gift": selected_gift,
        "alternatives": alternatives,
        "scoring_breakdown": scoring_breakdown,
        "status": "gifts_ranked"
    }
