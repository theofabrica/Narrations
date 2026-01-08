"""
Tests for MCP endpoint (Phase 1 MVP).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "MCP Narrations"
    assert "time" in data


def test_ping_action():
    """Test ping action."""
    response = client.post(
        "/mcp",
        json={
            "action": "ping",
            "payload": {"timestamp": "2024-01-01T00:00:00Z"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["action"] == "ping"
    assert data["data"]["message"] == "pong"
    assert "received_at" in data
    assert "completed_at" in data


def test_list_tools_action():
    """Test list_tools action."""
    response = client.post(
        "/mcp",
        json={
            "action": "list_tools"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["action"] == "list_tools"
    assert "actions" in data["data"]
    assert isinstance(data["data"]["actions"], list)
    assert "ping" in data["data"]["actions"]
    assert "list_tools" in data["data"]["actions"]
    assert "count" in data["data"]


def test_unknown_action():
    """Test unknown action returns error."""
    response = client.post(
        "/mcp",
        json={
            "action": "unknown_action_xyz",
            "payload": {}
        }
    )
    assert response.status_code == 200  # MCP returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert data["action"] == "unknown_action_xyz"
    assert data["error"] is not None
    assert data["error"]["code"] == "ACTION_NOT_FOUND"
    assert "Unknown action" in data["error"]["message"]


def test_missing_action():
    """Test missing action field."""
    response = client.post(
        "/mcp",
        json={
            "payload": {}
        }
    )
    # Should return 422 validation error from FastAPI
    assert response.status_code == 422


def test_request_with_trace():
    """Test request with trace information."""
    response = client.post(
        "/mcp",
        json={
            "action": "ping",
            "payload": {},
            "request_id": "test_req_123",
            "trace": {
                "project": "test_project",
                "user": "test_user",
                "session": "test_session"
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["request_id"] == "test_req_123"


def test_request_id_generation():
    """Test that request_id is generated if not provided."""
    response = client.post(
        "/mcp",
        json={
            "action": "ping",
            "payload": {}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] is not None
    assert data["request_id"].startswith("req_")
