"""
Gift Candidate Generator Node.
Generates 5-8 meaningfully diverse gift candidates tailored to user interests and budget.
Utilizes Gemini structured generation when active, with automatic fallback to a rich
deterministic catalog and matching heuristics.
"""

from typing import Dict, Any, List
import copy
from agent.catalog import CATALOG_ITEMS
from agent.llm_service import llm_service


def _calculate_catalog_relevance(item: Dict[str, Any], state: Dict[str, Any]) -> float:
    """Computes a heuristic matching score for catalog item selection."""
    score = 0.0
    user_interests = [i.lower().strip() for i in state.get("interests", [])]
    item_tags = [t.lower().strip() for t in item.get("tags", [])]
    
    # 1. Interest overlap
    matched_tags = 0
    for interest in user_interests:
        for tag in item_tags:
            if tag in interest or interest in tag:
                matched_tags += 1
    score += matched_tags * 25.0

    # 2. Budget proximity
    budget_min = state.get("budget_min", 0.0)
    budget_max = state.get("budget_max", 5000.0)
    item_min = item.get("estimated_cost_min", 0.0)
    item_max = item.get("estimated_cost_max", 0.0)
    item_mid = (item_min + item_max) / 2.0

    if item_min <= budget_max:
        if budget_min <= item_mid <= budget_max:
            score += 30.0  # Perfect fit
        elif item_mid < budget_min:
            score += 15.0  # Under budget (still affordable)
        elif item_min <= budget_max < item_max:
            score += 20.0  # Slight stretch but possible
    else:
        # Strictly exceeds budget
        score -= 50.0

    # 3. Occasion match
    user_occasion = state.get("occasion", "").lower()
    item_occasions = [o.lower() for o in item.get("suitable_occasions", [])]
    if any(user_occasion in occ or occ in user_occasion for occ in item_occasions):
        score += 15.0

    # 4. Relationship match
    user_rel = state.get("recipient", "").lower()
    item_rels = [r.lower() for r in item.get("suitable_relationships", [])]
    if any(user_rel in r or r in user_rel for r in item_rels):
        score += 10.0

    # 5. Gift purpose match
    user_prefs = [p.lower() for p in state.get("preferences", [])]
    item_purposes = [p.lower() for p in item.get("gift_purposes", [])]
    for pref in user_prefs:
        if any(pref in p or p in pref for p in item_purposes):
            score += 10.0

    # 6. Gift type match
    user_type = state.get("gift_type", "No preference").lower()
    item_types = [t.lower() for t in item.get("gift_types", [])]
    if user_type != "no preference":
        if any(user_type in t for t in item_types):
            score += 20.0
        else:
            score -= 15.0

    return score


def generate_candidate_gifts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main LangGraph node for Candidate Generation.
    Returns updated candidate_gifts and mode in state.
    """
    rejected_items = state.get("rejected_gifts", [])
    rejected_names = [r.get("gift_name", "").lower() for r in rejected_items]
    disliked = [d.lower() for d in state.get("disliked_items", [])]
    already_owned = [a.lower() for a in state.get("already_owned", [])]

    # Attempt Gemini generation first if available
    llm_candidates = None
    if llm_service.is_available():
        llm_candidates = llm_service.generate_candidates(
            user_state=state,
            rejected_names=rejected_names,
            count=6
        )

    if llm_candidates and len(llm_candidates) >= 3:
        # Gemini succeeded with structured output
        return {
            "candidate_gifts": llm_candidates,
            "mode": "gemini",
            "generation_attempts": state.get("generation_attempts", 0) + 1,
            "status": "candidates_generated"
        }

    # Deterministic fallback catalogue matching
    scored_catalog = []
    for item in CATALOG_ITEMS:
        name_lower = item["gift_name"].lower()
        cat_lower = item["gift_category"].lower()

        # Skip already owned or disliked
        if any(own in name_lower for own in already_owned if own):
            continue
        if any(dis in name_lower or dis in cat_lower for dis in disliked if dis):
            continue
        if any(rej in name_lower for rej in rejected_names if rej):
            continue

        relevance = _calculate_catalog_relevance(item, state)
        scored_catalog.append((relevance, item))

    # Sort descending by relevance
    scored_catalog.sort(key=lambda x: x[0], reverse=True)

    # Pick 5-8 candidates with category diversity enforcement
    selected: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}

    for score, item in scored_catalog:
        cat = item["gift_category"]
        if category_counts.get(cat, 0) >= 2 and len(selected) < 6:
            # Enforce diversity: max 2 per category until we fill basic quota
            continue

        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Build customized candidate
        matched_interests = [
            i for i in state.get("interests", [])
            if any(t.lower() in i.lower() or i.lower() in t.lower() for t in item.get("tags", []))
        ]
        matched_prefs = [
            p for p in state.get("preferences", [])
            if any(purp.lower() in p.lower() for purp in item.get("gift_purposes", []))
        ]

        why_text = (
            f"Tailored for {state.get('recipient')} on their {state.get('occasion')}. "
            f"Directly supports interest in {', '.join(matched_interests) if matched_interests else state.get('interests', ['their hobbies'])[0]}."
        )

        candidate = {
            "gift_name": item["gift_name"],
            "gift_category": item["gift_category"],
            "estimated_cost_min": float(item["estimated_cost_min"]),
            "estimated_cost_max": float(item["estimated_cost_max"]),
            "description": item["description"],
            "why_it_matches": why_text,
            "satisfied_interests": matched_interests if matched_interests else state.get("interests", [])[:1],
            "satisfied_preferences": matched_prefs if matched_prefs else state.get("preferences", [])[:1],
            "personalization_possibilities": item.get("personalization_possibilities", "Custom engraving available"),
            "practical_usefulness": item.get("practical_usefulness", 7),
            "sentimental_value": item.get("sentimental_value", 7),
            "potential_drawbacks": item.get("potential_drawbacks", "None noted"),
            "budget_fit_status": "Within budget" if item["estimated_cost_min"] <= state.get("budget_max", 5000) else "Slight stretch",
            "price_confidence_indicator": item.get("price_confidence_indicator", "High (standard market estimate)"),
            "verification_status": "Unverified market estimate - check local retail/e-commerce before purchase"
        }
        selected.append(candidate)
        if len(selected) >= 7:
            break

    # If too few candidates matched due to heavy filtering, pick closest items within budget
    if len(selected) < 4:
        for item in CATALOG_ITEMS:
            if item["gift_name"] not in [s["gift_name"] for s in selected]:
                if item["estimated_cost_min"] <= state.get("budget_max", 5000) * 1.2:
                    selected.append({
                        "gift_name": item["gift_name"],
                        "gift_category": item["gift_category"],
                        "estimated_cost_min": float(item["estimated_cost_min"]),
                        "estimated_cost_max": float(item["estimated_cost_max"]),
                        "description": item["description"],
                        "why_it_matches": f"Versatile option for {state.get('recipient')}.",
                        "satisfied_interests": state.get("interests", [])[:1],
                        "satisfied_preferences": state.get("preferences", [])[:1],
                        "personalization_possibilities": item.get("personalization_possibilities", ""),
                        "practical_usefulness": item.get("practical_usefulness", 7),
                        "sentimental_value": item.get("sentimental_value", 7),
                        "potential_drawbacks": item.get("potential_drawbacks", ""),
                        "budget_fit_status": "Within budget",
                        "price_confidence_indicator": item.get("price_confidence_indicator", "High (standard market estimate)"),
                        "verification_status": "Unverified market estimate - check local retail/e-commerce before purchase"
                    })
            if len(selected) >= 5:
                break

    return {
        "candidate_gifts": selected,
        "mode": "deterministic_fallback",
        "generation_attempts": state.get("generation_attempts", 0) + 1,
        "status": "candidates_generated"
    }
