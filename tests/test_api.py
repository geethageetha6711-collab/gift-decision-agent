"""
API integration tests for FastAPI endpoints.
Tests routes: /, /health, /workflow, /recommend, /recommend/{session_id},
/recommend/{session_id}/feedback, /recommend/{session_id}/report.
"""

import pytest
from fastapi.testclient import TestClient
from app import app, sessions

client = TestClient(app)


def test_get_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Gift Decision Agent" in response.text


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "mode" in data
    assert data["deterministic_fallback_ready"] is True


def test_get_workflow():
    response = client.get("/workflow")
    assert response.status_code == 200
    data = response.json()
    assert "main_workflow" in data
    assert "feedback_workflow" in data
    assert len(data["main_workflow"]["nodes"]) >= 5


def test_create_recommendation_and_download_pdf():
    payload = {
        "occasion": "Birthday",
        "recipient": "Best friend",
        "relationship": "Close",
        "budget_min": 500.0,
        "budget_max": 2000.0,
        "interests": ["photography", "music"],
        "preferences": ["Useful", "Memorable"],
        "disliked_items": [],
        "already_owned": [],
        "gift_type": "No preference"
    }

    # 1. POST /recommend
    res = client.post("/recommend", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "session_id" in data
    assert data["success"] is True
    session_id = data["session_id"]
    assert data["selected_gift"] is not None
    assert "gift_name" in data["selected_gift"]

    # 2. GET /recommend/{session_id}
    get_res = client.get(f"/recommend/{session_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["session_id"] == session_id

    # 3. POST /recommend/{session_id}/feedback
    fb_payload = {
        "reason": "Too expensive",
        "custom_feedback": "Please keep it strictly under ₹800",
        "rejected_gift_name": data["selected_gift"]["gift_name"]
    }
    fb_res = client.post(f"/recommend/{session_id}/feedback", json=fb_payload)
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["selected_gift"] is not None

    # 4. GET /recommend/{session_id}/report (PDF download)
    pdf_res = client.get(f"/recommend/{session_id}/report")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000  # Non-empty valid PDF bytes


def test_get_nonexistent_session_404():
    res = client.get("/recommend/non-existent-uuid")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_budget_validation():
    payload = {
        "occasion": "Birthday",
        "recipient": "Friend",
        "budget_min": 2000.0,
        "budget_max": 500.0,  # Max is less than min!
        "interests": ["tech"]
    }
    res = client.post("/recommend", json=payload)
    assert res.status_code == 422  # Unprocessable Entity
