import pytest
import openpyxl
from io import BytesIO
from app.services.excel_parser import parse_and_validate_excel, normalize_header


def create_mock_excel(headers: list, rows: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def test_header_normalization():
    assert normalize_header("Employee Name") == "employee_name"
    assert normalize_header("Emp_Name") == "employee_name"
    assert normalize_header("Role") == "designation"
    assert normalize_header("City") == "branch"
    assert normalize_header("Category") == "award_name"


def test_valid_excel_parsing():
    headers = ["employee_name", "designation", "branch", "award_name"]
    rows = [
        ["Alice Smith", "Engineer", "Pune", "Star Performer"],
        ["Bob Jones", "Manager", "Mumbai", "Excellence Award"],
    ]
    content = create_mock_excel(headers, rows)
    res = parse_and_validate_excel(content, "test.xlsx")

    assert res.valid is True
    assert res.total_rows == 2
    assert res.valid_rows == 2
    assert res.invalid_rows == 0
    assert res.duplicate_rows == 0
    assert len(res.records) == 2
    assert res.records[0].employee_name == "Alice Smith"


def test_missing_header():
    headers = ["employee_name", "branch"]  # missing designation & award_name
    rows = [["Alice", "Pune"]]
    content = create_mock_excel(headers, rows)
    res = parse_and_validate_excel(content, "test.xlsx")

    assert res.valid is False
    assert len(res.errors) > 0
    assert "Missing required columns" in res.errors[0].message


def test_duplicate_headers():
    headers = ["employee_name", "employee_name", "designation", "branch", "award_name"]
    rows = [["Alice", "Alice", "Engineer", "Pune", "Star Performer"]]
    content = create_mock_excel(headers, rows)
    res = parse_and_validate_excel(content, "test.xlsx")

    # Second employee_name should be ignored safely without overwriting the map
    assert res.valid is True
    assert res.records[0].employee_name == "Alice"



def test_missing_cell_value():
    headers = ["employee_name", "designation", "branch", "award_name"]
    rows = [
        ["Alice Smith", "", "Pune", "Star Performer"],  # missing designation
    ]
    content = create_mock_excel(headers, rows)
    res = parse_and_validate_excel(content, "test.xlsx")

    assert res.valid is False
    assert res.invalid_rows == 1
    assert res.records[0].is_valid is False
    assert "designation" in res.errors[0].column


def test_duplicate_row_detection():
    headers = ["employee_name", "designation", "branch", "award_name"]
    rows = [
        ["Alice Smith", "Engineer", "Pune", "Star Performer"],
        ["Alice Smith", "Engineer", "Pune", "Star Performer"],  # duplicate
    ]
    content = create_mock_excel(headers, rows)
    res = parse_and_validate_excel(content, "test.xlsx")

    assert res.duplicate_rows == 1
    assert res.records[1].is_valid is False
    assert "Duplicate record" in res.records[1].errors[0]


def test_corrupted_excel_file():
    res = parse_and_validate_excel(b"invalid binary content", "corrupted.xlsx")
    assert res.valid is False
    assert "Corrupted or invalid" in res.errors[0].message
