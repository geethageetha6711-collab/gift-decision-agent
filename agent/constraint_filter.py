"""
Constraint Filter Node.
Separates hard constraints from soft preferences.
Rejects candidates violating budget ceilings, explicit exclusions, already-owned items,
or mandatory gift types before scoring.
"""

from typing import Dict, Any, List, Tuple


def filter_constraints(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates candidate gifts against strict hard constraints.
    Populates filtered_candidates and rejected_candidates.
    """
    candidates = state.get("candidate_gifts", [])
    budget_max = float(state.get("budget_max", 100000.0))
    disliked_items = [d.lower().strip() for d in state.get("disliked_items", []) if d.strip()]
    already_owned = [a.lower().strip() for a in state.get("already_owned", []) if a.strip()]
    gift_type = state.get("gift_type", "No preference").lower().strip()
    rejected_gifts_history = [r.get("gift_name", "").lower().strip() for r in state.get("rejected_gifts", [])]

    # Explicit hard constraint dictionary for state transparency
    hard_constraints = {
        "budget_ceiling_inr": budget_max,
        "excluded_terms": disliked_items,
        "already_owned_items": already_owned,
        "mandatory_gift_type": gift_type if gift_type != "no preference" else None,
        "previously_rejected_names": rejected_gifts_history
    }

    soft_preferences = {
        "interests": state.get("interests", []),
        "desired_purposes": state.get("preferences", []),
        "preferred_style": state.get("preferred_style", ""),
        "relationship_closeness": state.get("relationship", "Close")
    }

    filtered: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    warning_messages = list(state.get("warning_messages", []))

    for item in candidates:
        name = item.get("gift_name", "")
        name_lower = name.lower()
        category_lower = item.get("gift_category", "").lower()
        desc_lower = item.get("description", "").lower()
        cost_min = float(item.get("estimated_cost_min", 0.0))
        cost_max = float(item.get("estimated_cost_max", cost_min))
        cost_mid = (cost_min + cost_max) / 2.0

        violation = None

        # 1. Hard Budget Constraint: minimum cost cannot exceed user's maximum budget
        if cost_min > budget_max:
            violation = f"Minimum cost (₹{int(cost_min):,}) exceeds your maximum budget of ₹{int(budget_max):,}."
        elif cost_mid > budget_max * 1.15:
            violation = f"Estimated average cost (₹{int(cost_mid):,}) significantly exceeds maximum budget of ₹{int(budget_max):,}."

        # 2. Hard Exclusion Constraint: user explicitly disliked or wants to avoid
        if not violation and disliked_items:
            for dis in disliked_items:
                if dis in name_lower or dis in category_lower or dis in desc_lower:
                    violation = f"Violates exclusion rule: matches disliked item/category '{dis}'."
                    break

        # 3. Already Owned Constraint
        if not violation and already_owned:
            for own in already_owned:
                if own in name_lower or own in desc_lower:
                    violation = f"Violates ownership rule: recipient already owns '{own}'."
                    break

        # 4. Previously Rejected Items (from interactive feedback loops)
        if not violation and rejected_gifts_history:
            for rej in rejected_gifts_history:
                if rej in name_lower or name_lower in rej:
                    violation = f"Previously rejected by user in this session ('{name}')."
                    break

        # 5. Mandatory Gift Type (when user strictly requires e.g. "Experience" or "Handmade")
        if not violation and gift_type != "no preference":
            # Check if candidate mentions or supports this gift type
            item_desc_cat = f"{category_lower} {desc_lower} {item.get('personalization_possibilities', '').lower()}"
            if gift_type == "personalized":
                if not item.get("personalization_possibilities") and "personal" not in item_desc_cat:
                    violation = f"Candidate does not support required gift type: 'Personalized'."
            elif gift_type == "experience":
                if "experience" not in category_lower and "workshop" not in item_desc_cat and "pass" not in name_lower:
                    violation = f"Candidate is not an experiential gift as required ('Experience')."
            elif gift_type == "handmade":
                if "handmade" not in item_desc_cat and "handcrafted" not in item_desc_cat and "craft" not in item_desc_cat:
                    violation = f"Candidate is not handcrafted as required ('Handmade')."

        if violation:
            rejected.append({
                "candidate": item,
                "reason": violation
            })
        else:
            # Update budget fit status accurately
            if cost_max <= budget_max:
                item["budget_fit_status"] = "Under budget" if cost_max < budget_max * 0.6 else "Within budget"
            else:
                item["budget_fit_status"] = "Slight stretch"
            filtered.append(item)

    needs_regeneration = False
    if len(filtered) < 3:
        needs_regeneration = True
        warning = f"Only {len(filtered)} candidate(s) passed all hard constraints. Regeneration requested."
        if warning not in warning_messages:
            warning_messages.append(warning)

    if len(filtered) == 0:
        warning = f"Zero candidates survived hard constraints (Max budget: ₹{budget_max:,}). Consider relaxing constraints."
        if warning not in warning_messages:
            warning_messages.append(warning)

    return {
        "hard_constraints": hard_constraints,
        "soft_preferences": soft_preferences,
        "filtered_candidates": filtered,
        "rejected_candidates": rejected,
        "needs_regeneration": needs_regeneration,
        "warning_messages": warning_messages,
        "status": "constraints_filtered"
    }
