import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_excel_parser import create_mock_excel
from tests.test_template_inspector import create_mock_pptx

client = TestClient(app)


def test_strict_hex_id_validation():
    # Non-hex alphanumeric string should be rejected by 32-char hex pattern
    res = client.get("/api/templates/invalid_non_hex_id_1234567890/readiness")
    assert res.status_code == 400
    assert "Invalid file identifier format" in res.json()["detail"]


def test_path_traversal_rejection():
    res = client.get("/api/generations/..%2F..%2Fetc%2Fpasswd/download")
    assert res.status_code in [400, 404]
