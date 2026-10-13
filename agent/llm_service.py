"""
Google Gemini integration service using langchain-google-genai.
Handles structured candidate generation, feedback analysis, and personalized reasoning.
Falls back safely to deterministic methods if Gemini is unconfigured or encounters API issues.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Ensure environment variables are loaded securely
load_dotenv()

logger = logging.getLogger("gift_agent.llm_service")

# Pydantic schema for structured output from Gemini
class LLMGiftCandidate(BaseModel):
    gift_name: str = Field(..., description="Specific gift name, e.g. 'Personalized Wooden Memory Album'")
    gift_category: str = Field(..., description="Gift category e.g. 'Personalized Keepsakes', 'Tech & Gadgets'")
    estimated_cost_min: float = Field(..., description="Estimated minimum cost in INR")
    estimated_cost_max: float = Field(..., description="Estimated maximum cost in INR")
    description: str = Field(..., description="2-3 sentence engaging description of what the item is")
    why_it_matches: str = Field(..., description="Direct reasoning explaining why this fits the recipient's interests and occasion")
    satisfied_interests: List[str] = Field(default_factory=list, description="Specific interests matched")
    satisfied_preferences: List[str] = Field(default_factory=list, description="Specific gift purposes matched e.g. Sentimental, Useful")
    personalization_possibilities: str = Field(default="", description="Specific ways this gift can be customized")
    practical_usefulness: int = Field(default=7, ge=1, le=10, description="Usefulness rating 1-10")
    sentimental_value: int = Field(default=7, ge=1, le=10, description="Sentimental depth 1-10")
    potential_drawbacks: str = Field(default="", description="Trade-offs, limitations, or caveats")


class LLMCandidateList(BaseModel):
    candidates: List[LLMGiftCandidate] = Field(..., description="List of 5 to 8 distinct gift candidates")


class LLMFeedbackAnalysis(BaseModel):
    preference_adjustments: Dict[str, Any] = Field(default_factory=dict, description="Changes in weight or preferred attributes")
    constraints_to_add: List[str] = Field(default_factory=list, description="New categories or items to strictly exclude")
    explanation_of_shift: str = Field(..., description="Natural language explanation of how the recommendation is shifting")


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        self._client = None
        self._initialized = False

    def is_available(self) -> bool:
        """Checks if a valid, non-placeholder API key is set."""
        if not self.api_key:
            return False
        if "your_gemini_api_key" in self.api_key.lower() or len(self.api_key) < 15:
            return False
        return True

    def _get_chat_model(self):
        """Initializes or retrieves the LangChain ChatGoogleGenerativeAI instance."""
        if not self.is_available():
            return None
        if self._client is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._client = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.4,
                    max_retries=2,
                    timeout=20,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatGoogleGenerativeAI: {e}")
                self._client = None
        return self._client

    def generate_candidates(
        self,
        user_state: Dict[str, Any],
        rejected_names: List[str],
        count: int = 6
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Uses Gemini to generate 5-8 creative, diverse gift candidates adhering to
        budget, interests, preferences, and exclusions.
        """
        model = self._get_chat_model()
        if not model:
            return None

        prompt = f"""
You are an expert gift decision assistant for India.
Generate {count} distinct, creative, and thoughtful gift recommendations matching these exact details:

Recipient: {user_state.get('recipient')} (Relationship closeness: {user_state.get('relationship', 'Close')})
Occasion: {user_state.get('occasion')}
Budget Range: INR ₹{user_state.get('budget_min', 500)} to ₹{user_state.get('budget_max', 3000)}
Interests: {', '.join(user_state.get('interests', []))}
Preferred Gift Purposes: {', '.join(user_state.get('preferences', []))}
Preferred Gift Type: {user_state.get('gift_type', 'No preference')}
Style / Colors: {user_state.get('preferred_style', 'None specified')}
Optional Notes: {user_state.get('optional_notes', 'None')}

CRITICAL CONSTRAINTS:
1. Hard Budget Limit: Do NOT suggest gifts whose estimated price exceeds ₹{user_state.get('budget_max')}.
2. Items / Categories to Avoid: {', '.join(user_state.get('disliked_items', []))}
3. Items Already Owned: {', '.join(user_state.get('already_owned', []))}
4. Previously Rejected Items: {', '.join(rejected_names)}
5. Diversity: Provide items across DIFFERENT categories (e.g. tech, handmade, keepsake, gourmet, experience). Avoid suggesting repetitive variations of the same idea.
6. Realism: Realistic estimated INR prices in India (e-commerce or local craft markets). Never invent live store inventories.

Format your output as a valid JSON object matching this schema:
{{
  "candidates": [
    {{
      "gift_name": "string",
      "gift_category": "string",
      "estimated_cost_min": number,
      "estimated_cost_max": number,
      "description": "string",
      "why_it_matches": "string",
      "satisfied_interests": ["string"],
      "satisfied_preferences": ["string"],
      "personalization_possibilities": "string",
      "practical_usefulness": integer between 1 and 10,
      "sentimental_value": integer between 1 and 10,
      "potential_drawbacks": "string"
    }}
  ]
}}
Respond ONLY with the JSON object. Do not include markdown code fence formatting or surrounding conversational text.
"""
        try:
            response = model.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            
            # Clean up markdown tags if present
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()

            data = json.loads(cleaned_content)
            # Validate through Pydantic
            parsed = LLMCandidateList.model_validate(data)
            results = []
            for c in parsed.candidates:
                results.append({
                    "gift_name": c.gift_name,
                    "gift_category": c.gift_category,
                    "estimated_cost_min": float(c.estimated_cost_min),
                    "estimated_cost_max": float(c.estimated_cost_max),
                    "description": c.description,
                    "why_it_matches": c.why_it_matches,
                    "satisfied_interests": c.satisfied_interests,
                    "satisfied_preferences": c.satisfied_preferences,
                    "personalization_possibilities": c.personalization_possibilities,
                    "practical_usefulness": c.practical_usefulness,
                    "sentimental_value": c.sentimental_value,
                    "potential_drawbacks": c.potential_drawbacks,
                    "budget_fit_status": "Within budget",
                    "price_confidence_indicator": "High (Gemini AI estimated market range)",
                    "verification_status": "AI estimated market range - verify with local retailers before purchase"
                })
            if results:
                return results
        except Exception as e:
            logger.warning(f"Gemini candidate generation failed or timed out: {e}. Falling back to deterministic catalog.")
        
        return None

    def explain_decision(
        self,
        selected_gift: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        user_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        Uses Gemini to generate an articulate, nuanced explanation of why the top gift was chosen,
        highlighting trade-offs with alternatives.
        """
        model = self._get_chat_model()
        if not model:
            return None

        alt_summary = "\n".join([
            f"- {a.get('gift_name')} ({a.get('gift_category')}, ₹{int(a.get('estimated_cost_min',0))}-₹{int(a.get('estimated_cost_max',0))}): Score {a.get('total_score',0)}/100. Trade-off: {', '.join(a.get('trade_offs', ['Alternative option']))}"
            for a in alternatives[:3]
        ])

        prompt = f"""
You are the Decision Reviewer for a personalized gift advisory system.
Write an objective, insightful, and structured justification (3-4 paragraphs) explaining why '{selected_gift.get('gift_name')}' emerged as the best recommendation.

User Context:
- Recipient: {user_state.get('recipient')} ({user_state.get('relationship', 'Close')})
- Occasion: {user_state.get('occasion')}
- Budget: ₹{user_state.get('budget_min')} – ₹{user_state.get('budget_max')}
- Interests: {', '.join(user_state.get('interests', []))}
- Stated Purposes: {', '.join(user_state.get('preferences', []))}

Selected Top Gift:
- Name: {selected_gift.get('gift_name')}
- Category: {selected_gift.get('gift_category')}
- Estimated Cost: ₹{int(selected_gift.get('estimated_cost_min',0))} – ₹{int(selected_gift.get('estimated_cost_max',0))}
- Match Score: {selected_gift.get('total_score', 0)}/100
- Why it matches: {selected_gift.get('why_it_matches')}
- Potential Drawbacks: {selected_gift.get('potential_drawbacks')}
- Personalization: {selected_gift.get('personalization_possibilities')}

Close Alternatives:
{alt_summary}

Requirements:
1. Explain specifically why this gift best balances the recipient's interests with the budget and occasion.
2. Directly contrast it with the alternatives, articulating the specific trade-offs (e.g. utility vs sentimental depth).
3. Be transparent about any potential caveats or drawbacks.
4. Do NOT promise guaranteed satisfaction; frame it as the best-supported decision based on the provided criteria.
"""
        try:
            response = model.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            return content.strip()
        except Exception as e:
            logger.warning(f"Gemini decision explanation failed: {e}")
            return None

    def analyze_feedback(
        self,
        feedback_reason: str,
        custom_feedback: str,
        rejected_gift: Optional[Dict[str, Any]],
        current_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini to analyze user feedback and extract updated preferences and constraints.
        """
        model = self._get_chat_model()
        if not model:
            return None

        prompt = f"""
The user has rejected a gift recommendation or provided critical feedback.
Rejected Gift: {rejected_gift.get('gift_name') if rejected_gift else 'Top Recommendation'}
Category: {rejected_gift.get('gift_category') if rejected_gift else 'Unknown'}
Feedback Reason: {feedback_reason}
User's Additional Note: {custom_feedback}

Current Preferences:
- Budget: ₹{current_state.get('budget_min')} - ₹{current_state.get('budget_max')}
- Interests: {', '.join(current_state.get('interests', []))}
- Purposes: {', '.join(current_state.get('preferences', []))}

Analyze how preferences and constraints should adapt.
For example:
- If 'Too expensive': adjust budget expectations downward or favor high-value budget options.
- If 'Not my style' or 'Too generic': demand more specialized, creative, or unconventional categories.
- If 'Already owns it': strictly exclude this item and similar items.
- If 'Try a different category': exclude category '{rejected_gift.get('gift_category') if rejected_gift else ''}'.
- If 'More practical': increase weight for utility and decrease pure sentimental trinkets.

Output JSON:
{{
  "preference_adjustments": {{
    "favored_purpose": "Useful / Sentimental / Creative / Practical",
    "budget_note": "string"
  }},
  "constraints_to_add": ["category or item string to exclude"],
  "explanation_of_shift": "2-3 sentences explaining how the agent is adjusting its decision criteria"
}}
Respond ONLY with the JSON object.
"""
        try:
            response = model.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()

            data = json.loads(cleaned_content)
            parsed = LLMFeedbackAnalysis.model_validate(data)
            return {
                "preference_adjustments": parsed.preference_adjustments,
                "constraints_to_add": parsed.constraints_to_add,
                "explanation_of_shift": parsed.explanation_of_shift
            }
        except Exception as e:
            logger.warning(f"Gemini feedback analysis failed: {e}")
            return None


# Global singleton instance
llm_service = LLMService()
