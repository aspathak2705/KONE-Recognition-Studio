from pydantic import BaseModel, Field
from typing import List, Optional


class RecognitionRecord(BaseModel):
    row_number: int
    employee_name: str
    designation: str
    branch: str
    award_name: str
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)


class ValidationErrorItem(BaseModel):
    row: int
    column: str
    message: str


class ExcelValidationResponse(BaseModel):
    valid: bool
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    records: List[RecognitionRecord] = Field(default_factory=list)
    saved_path: Optional[str] = None


class FieldSchemaInfo(BaseModel):
    field_name: str
    canonical_header: str
    accepted_aliases: List[str]
    required: bool
    description: str


class SchemaResponse(BaseModel):
    required_fields: List[FieldSchemaInfo]
    accepted_formats: List[str]
    rules: List[str]
