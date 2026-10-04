from pathlib import Path
from app.schemas.recognition import RecognitionRecord
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, SlotMappingDetail
from app.services.pptx_generator import generate_powerpoint_presentation
from app.services.template_registry_service import template_registry

# Load Real Template Binaries
q4_dir = template_registry._get_template_dir("f27b8666ba9d4dd0bd8d383581ba31ba")
nj_dir = template_registry._get_template_dir("046f2871d4ee4c53b2ee3d469a795432")

with open(q4_dir / "master_v1.pptx", "rb") as f:
    q4_bytes = f.read()

with open(nj_dir / "master_v1.pptx", "rb") as f:
    nj_bytes = f.read()

# 1. New Joiner 7-card mapping test
nj_slots = [
    SlotMappingDetail(
        slot_index=0,
        employee_name=FieldMappingDetail(shape_name="TextBox 8"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 24"),
    ),
    SlotMappingDetail(
        slot_index=1,
        employee_name=FieldMappingDetail(shape_name="TextBox 12"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 26"),
    ),
    SlotMappingDetail(
        slot_index=2,
        employee_name=FieldMappingDetail(shape_name="TextBox 16"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 28"),
    ),
    SlotMappingDetail(
        slot_index=3,
        employee_name=FieldMappingDetail(shape_name="TextBox 18"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 30"),
    ),
    SlotMappingDetail(
        slot_index=4,
        employee_name=FieldMappingDetail(shape_name="TextBox 20"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 32"),
    ),
    SlotMappingDetail(
        slot_index=5,
        employee_name=FieldMappingDetail(shape_name="TextBox 22"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 34"),
    ),
    SlotMappingDetail(
        slot_index=6,
        employee_name=FieldMappingDetail(shape_name="TextBox 40"),
        photo_placeholder=FieldMappingDetail(shape_name="Picture 42"),
    ),
]

nj_mapping = FieldMappingConfig(template_slide_index=0, slots=nj_slots)

# Test datasets: 1, 5, 7, 8 employees
for n in [1, 5, 7, 8]:
    recs = [
        RecognitionRecord(
            row_number=i,
            employee_name=f"New Joiner {i}",
            designation=f"Role {i}",
            branch="Mumbai",
            award_name="Onboarding",
            is_valid=True,
        )
        for i in range(1, n + 1)
    ]
    res = generate_powerpoint_presentation(
        template_content=nj_bytes,
        template_filename="New Joiner Template.pptx",
        excel_records=recs,
        mapping_config=nj_mapping,
        source_excel_file_id=f"excel_{n}",
        source_template_file_id="046f2871d4ee4c53b2ee3d469a795432",
    )
    print(f"New Joiner {n} records -> generated slides: {res.slide_count}, file: {res.generated_file_id}")

# 2. Q4 Template test
q4_mapping = FieldMappingConfig(
    template_slide_index=1,  # Slide 2: 2-card layout (Picture 5, Picture 19)
    slots=[
        SlotMappingDetail(
            slot_index=0,
            employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"),
            photo_placeholder=FieldMappingDetail(shape_name="Picture 5"),
        ),
        SlotMappingDetail(
            slot_index=1,
            employee_name=FieldMappingDetail(shape_name="Text Placeholder 8"),
            photo_placeholder=FieldMappingDetail(shape_name="Picture 19"),
        ),
    ]
)

for n in [1, 2, 5]:
    recs = [
        RecognitionRecord(
            row_number=i,
            employee_name=f"KONE Winner {i}",
            designation=f"Senior Engineer {i}",
            branch="Pune",
            award_name="Q4 Excellence",
            is_valid=True,
        )
        for i in range(1, n + 1)
    ]
    res = generate_powerpoint_presentation(
        template_content=q4_bytes,
        template_filename="Q4 R&R 2025.pptx",
        excel_records=recs,
        mapping_config=q4_mapping,
        source_excel_file_id=f"q4_excel_{n}",
        source_template_file_id="f27b8666ba9d4dd0bd8d383581ba31ba",
    )
    print(f"Q4 R&R {n} records -> generated slides: {res.slide_count}, file: {res.generated_file_id}")
