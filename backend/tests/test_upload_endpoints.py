import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_excel_parser import create_mock_excel
from tests.test_template_inspector import create_mock_pptx

client = TestClient(app)


def test_schema_endpoint():
    res = client.get("/api/recognitions/schema")
    assert res.status_code == 200
    data = res.json()
    assert len(data["required_fields"]) == 4
    assert data["accepted_formats"] == [".xlsx"]


def test_validate_excel_endpoint_valid():
    headers = ["employee_name", "designation", "branch", "award_name"]
    rows = [["John Doe", "Lead Engineer", "Chennai", "Spotlight Award"]]
    content = create_mock_excel(headers, rows)

    files = {"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = client.post("/api/recognitions/validate-excel", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_rows"] == 1
    assert data["records"][0]["employee_name"] == "John Doe"
    assert data["file_id"] is not None
    assert data["saved_path"] is None


def test_validate_excel_endpoint_invalid_ext():
    files = {"file": ("test.txt", b"plain text", "text/plain")}
    res = client.post("/api/recognitions/validate-excel", files=files)
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_inspect_template_endpoint_valid():
    content = create_mock_pptx()
    files = {"file": ("template.pptx", content, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    res = client.post("/api/templates/inspect", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["slide_count"] == 1
    assert data["template_id"] is not None
    assert data["saved_path"] is None

