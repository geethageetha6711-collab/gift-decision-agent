"""
FastAPI Application for Geetha's Gift Decision Agent.
Serves interactive frontend, LangGraph execution endpoints, feedback loops, and PDF exports.
"""

import os
import uuid
from typing import Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.state import GiftPreferencesInput, FeedbackInput, GiftAgentState
from agent.graph import create_gift_agent_graph, create_feedback_graph
from agent.llm_service import llm_service
from services.report_service import generate_gift_decision_pdf

# In-memory storage for active sessions (persists for runtime lifecycle; resets on server restart)
sessions: Dict[str, Dict[str, Any]] = {}

# Compile LangGraph workflows
gift_agent_graph = create_gift_agent_graph()
feedback_graph = create_feedback_graph()

app = FastAPI(
    title="Gift Decision Agent",
    description="Intelligent AI Gift Decision Engine powered by LangGraph, Gemini, and Deterministic Scoring",
    version="1.0.0"
)

# CORS middleware for development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main interactive gift advisor web application."""
    index_file = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(index_file):
        raise HTTPException(status_code=404, detail="Frontend template not found.")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health_check():
    """Returns runtime health status and active reasoning engine mode."""
    mode = "gemini" if llm_service.is_available() else "deterministic_fallback"
    return {
        "status": "healthy",
        "service": "Gift Decision Agent",
        "mode": mode,
        "model": llm_service.model_name if mode == "gemini" else "Deterministic Catalogue Engine",
        "active_sessions": len(sessions),
        "deterministic_fallback_ready": True
    }


@app.get("/workflow")
async def get_workflow_schema():
    """Returns the visual architectural layout and conditional edge mapping of the LangGraph workflows."""
    return {
        "main_workflow": {
            "entry_point": "preference_validator",
            "nodes": [
                {"id": "preference_validator", "label": "Preference Validator", "type": "Validation"},
                {"id": "candidate_generator", "label": "Candidate Generator", "type": "Generation"},
                {"id": "constraint_filter", "label": "Constraint Filter", "type": "Hard Filtering"},
                {"id": "scoring_engine", "label": "Deterministic Scoring Engine", "type": "Scoring"},
                {"id": "decision_reviewer", "label": "Decision Reviewer", "type": "Review & Audit"},
                {"id": "final_recommendation", "label": "Final Recommendation Synthesis", "type": "Output"}
            ],
            "edges": [
                {"from": "START", "to": "preference_validator"},
                {"from": "preference_validator", "to": "candidate_generator"},
                {"from": "candidate_generator", "to": "constraint_filter"},
                {"from": "constraint_filter", "to": "candidate_generator", "conditional": True, "condition": "needs_regeneration (< 3 valid candidates)"},
                {"from": "constraint_filter", "to": "scoring_engine", "conditional": True, "condition": "valid candidates >= 3"},
                {"from": "scoring_engine", "to": "decision_reviewer"},
                {"from": "decision_reviewer", "to": "candidate_generator", "conditional": True, "condition": "review_failed & attempts < 3"},
                {"from": "decision_reviewer", "to": "final_recommendation", "conditional": True, "condition": "review_passed or attempts >= 3"},
                {"from": "final_recommendation", "to": "END"}
            ]
        },
        "feedback_workflow": {
            "entry_point": "feedback_analyzer",
            "nodes": [
                {"id": "feedback_analyzer", "label": "Feedback Analyzer", "type": "Analysis"},
                {"id": "preference_updater", "label": "Preference & Constraint Updater", "type": "Adaptation"},
                {"id": "candidate_regenerator", "label": "Candidate Regenerator", "type": "Generation"},
                {"id": "constraint_filter", "label": "Constraint Filter", "type": "Hard Filtering"},
                {"id": "scoring_engine", "label": "Scoring Engine", "type": "Scoring"},
                {"id": "decision_reviewer", "label": "Decision Reviewer", "type": "Review"},
                {"id": "final_recommendation", "label": "Updated Recommendation", "type": "Output"}
            ],
            "edges": [
                {"from": "START", "to": "feedback_analyzer"},
                {"from": "feedback_analyzer", "to": "preference_updater"},
                {"from": "preference_updater", "to": "candidate_regenerator"},
                {"from": "candidate_regenerator", "to": "constraint_filter"},
                {"from": "constraint_filter", "to": "scoring_engine"},
                {"from": "scoring_engine", "to": "decision_reviewer"},
                {"from": "decision_reviewer", "to": "final_recommendation"},
                {"from": "final_recommendation", "to": "END"}
            ]
        }
    }


@app.post("/recommend", status_code=status.HTTP_201_CREATED)
async def create_recommendation(payload: GiftPreferencesInput):
    """
    Creates a new gift recommendation session and executes the full LangGraph decision workflow.
    """
    session_id = payload.session_id or str(uuid.uuid4())

    initial_state: GiftAgentState = {
        "session_id": session_id,
        "occasion": payload.occasion,
        "recipient": payload.recipient,
        "relationship": payload.relationship,
        "budget_min": float(payload.budget_min),
        "budget_max": float(payload.budget_max),
        "interests": payload.interests,
        "preferences": payload.preferences,
        "disliked_items": payload.disliked_items,
        "already_owned": payload.already_owned,
        "gift_type": payload.gift_type,
        "preferred_style": payload.preferred_style or "",
        "age_range": payload.age_range or "",
        "deadline": payload.deadline or "",
        "optional_notes": payload.optional_notes or "",
        "hard_constraints": {},
        "soft_preferences": {},
        "candidate_gifts": [],
        "filtered_candidates": [],
        "rejected_candidates": [],
        "scoring_breakdown": {},
        "ranked_gifts": [],
        "selected_gift": None,
        "alternatives": [],
        "rejected_gifts": [],
        "feedback_history": [],
        "updated_preferences": {},
        "generation_attempts": 0,
        "decision_explanation": "",
        "review_notes": [],
        "warning_messages": [],
        "needs_regeneration": False,
        "mode": "gemini" if llm_service.is_available() else "deterministic_fallback",
        "status": "initiated",
        "final_report": {}
    }

    try:
        final_state = gift_agent_graph.invoke(initial_state)
        # Store state in memory
        sessions[session_id] = final_state
        return final_state.get("final_report", final_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution encountered an error: {str(e)}"
        )


@app.get("/recommend/{session_id}")
async def get_recommendation_session(session_id: str):
    """Retrieves session results, decision report, and feedback history."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found. Note that session states reset on server restart."
        )
    session_data = sessions[session_id]
    return session_data.get("final_report", session_data)


@app.post("/recommend/{session_id}/feedback")
async def submit_feedback(session_id: str, feedback: FeedbackInput):
    """
    Submits user feedback or rejection reason, updates preference state,
    and runs the LangGraph feedback workflow to deliver an adapted recommendation.
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    current_state = sessions[session_id]
    
    # Record feedback item
    history = list(current_state.get("feedback_history", []))
    history.append({
        "reason": feedback.reason,
        "custom_feedback": feedback.custom_feedback or "",
        "rejected_gift_name": feedback.rejected_gift_name or (current_state.get("selected_gift", {}).get("gift_name", ""))
    })
    current_state["feedback_history"] = history

    try:
        updated_state = feedback_graph.invoke(current_state)
        sessions[session_id] = updated_state
        return updated_state.get("final_report", updated_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback adaptation workflow failed: {str(e)}"
        )


@app.get("/recommend/{session_id}/report")
async def download_report_pdf(session_id: str):
    """Generates and downloads a professional PDF decision report for the session."""
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    session_data = sessions[session_id]
    pdf_buffer = generate_gift_decision_pdf(session_data)

    filename = f"Gift_Decision_Report_{session_id[:8]}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
