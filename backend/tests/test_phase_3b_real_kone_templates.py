import pytest
from pathlib import Path
from app.schemas.recognition import RecognitionRecord
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, SlotMappingDetail
from app.services.pptx_generator import generate_powerpoint_presentation
from app.services.template_registry_service import template_registry

Q4_TEMPLATE_ID = "f27b8666ba9d4dd0bd8d383581ba31ba"
NJ_TEMPLATE_ID = "046f2871d4ee4c53b2ee3d469a795432"


@pytest.fixture
def nj_template_bytes():
    nj_dir = template_registry._get_template_dir(NJ_TEMPLATE_ID)
    with open(nj_dir / "master_v1.pptx", "rb") as f:
        return f.read()


@pytest.fixture
def q4_template_bytes():
    q4_dir = template_registry._get_template_dir(Q4_TEMPLATE_ID)
    with open(q4_dir / "master_v1.pptx", "rb") as f:
        return f.read()


def test_real_kone_new_joiner_acceptance(nj_template_bytes):
    slots = [
        SlotMappingDetail(
            slot_index=i,
            employee_name=FieldMappingDetail(shape_name=f"TextBox {shape_id}"),
            photo_placeholder=FieldMappingDetail(shape_name=f"Picture {pic_id}"),
        )
        for i, (shape_id, pic_id) in enumerate([
            (8, 24), (12, 26), (16, 28), (18, 30), (20, 32), (22, 34), (40, 42)
        ])
    ]
    mapping = FieldMappingConfig(template_slide_index=0, slots=slots)

    # 1 Employee -> 1 slide
    recs_1 = [RecognitionRecord(row_number=1, employee_name="Employee 1", designation="Role 1", branch="Location 1", award_name="New Joiner", is_valid=True)]
    res_1 = generate_powerpoint_presentation(nj_template_bytes, "New Joiner Template.pptx", recs_1, mapping, "excel_1", NJ_TEMPLATE_ID)
    assert res_1.slide_count == 1
    assert res_1.record_count == 1

    # 7 Employees -> 1 slide (capacity)
    recs_7 = [RecognitionRecord(row_number=i, employee_name=f"Employee {i}", designation=f"Role {i}", branch="Location 1", award_name="New Joiner", is_valid=True) for i in range(1, 8)]
    res_7 = generate_powerpoint_presentation(nj_template_bytes, "New Joiner Template.pptx", recs_7, mapping, "excel_7", NJ_TEMPLATE_ID)
    assert res_7.slide_count == 1
    assert res_7.record_count == 7

    # 8 Employees -> 2 slides (overflow)
    recs_8 = [RecognitionRecord(row_number=i, employee_name=f"Employee {i}", designation=f"Role {i}", branch="Location 1", award_name="New Joiner", is_valid=True) for i in range(1, 9)]
    res_8 = generate_powerpoint_presentation(nj_template_bytes, "New Joiner Template.pptx", recs_8, mapping, "excel_8", NJ_TEMPLATE_ID)
    assert res_8.slide_count == 2
    assert res_8.record_count == 8


def test_real_kone_q4_rr_acceptance(q4_template_bytes):
    slots = [
        SlotMappingDetail(slot_index=0, employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"), photo_placeholder=FieldMappingDetail(shape_name="Picture 5")),
        SlotMappingDetail(slot_index=1, employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"), photo_placeholder=FieldMappingDetail(shape_name="Picture 19")),
    ]
    mapping = FieldMappingConfig(template_slide_index=1, slots=slots)

    recs_2 = [RecognitionRecord(row_number=i, employee_name=f"Winner {i}", designation=f"Engineer {i}", branch="Pune", award_name="Q4 R&R", is_valid=True) for i in range(1, 3)]
    res_2 = generate_powerpoint_presentation(q4_template_bytes, "Q4 R&R 2025.pptx", recs_2, mapping, "excel_q4_2", Q4_TEMPLATE_ID)
    assert res_2.record_count == 2
    assert res_2.status == "completed"
