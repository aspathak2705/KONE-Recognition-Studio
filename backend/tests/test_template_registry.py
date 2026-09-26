import pytest
from io import BytesIO
from pptx import Presentation
from app.services.template_registry_service import TemplateRegistryService, calculate_pptx_hash
from app.schemas.mapping import FieldMappingConfig, FieldMappingDetail, GenerationReadiness
from app.schemas.template_registry import TemplateMetadata


def create_mock_pptx_bytes(title_text: str = "Employee Name") -> bytes:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tx_box = slide.shapes.add_textbox(0, 0, 100, 50)
    tx_box.name = "EmployeeName"
    tx_box.text_frame.text = title_text
    out = BytesIO()
    prs.save(out)
    return out.getvalue()


@pytest.fixture
def tmp_registry(tmp_path):
    reg_dir = tmp_path / "templates"
    return TemplateRegistryService(registry_dir=reg_dir)


def test_register_new_template_and_hash(tmp_registry):
    content = create_mock_pptx_bytes("John Doe")
    expected_hash = calculate_pptx_hash(content)

    res = tmp_registry.register_or_update_template(
        name="KONE Quarterly Recognition",
        content=content,
        filename="kone_master.pptx",
    )

    assert res.is_new_version is True
    assert res.is_duplicate_hash is False
    assert res.template.name == "KONE Quarterly Recognition"
    assert res.template.current_version == 1
    assert res.template.file_hash == expected_hash
    assert len(res.template.versions) == 1
    assert res.active_version.version_number == 1


def test_duplicate_pptx_hash_reuses_version(tmp_registry):
    content = create_mock_pptx_bytes("Identical Binary")

    res1 = tmp_registry.register_or_update_template(
        name="KONE Master",
        content=content,
        filename="master.pptx",
    )

    res2 = tmp_registry.register_or_update_template(
        name="KONE Master Second Upload",
        content=content,
        filename="master_copy.pptx",
    )

    assert res2.is_duplicate_hash is True
    assert res2.is_new_version is False
    assert res2.template.template_id == res1.template.template_id
    assert res2.active_version.version_number == 1


def test_new_version_created_on_different_hash(tmp_registry):
    content1 = create_mock_pptx_bytes("Version 1 Text")
    content2 = create_mock_pptx_bytes("Version 2 Modified Text")

    res1 = tmp_registry.register_or_update_template(
        name="KONE Award Template",
        content=content1,
        filename="v1.pptx",
    )

    res2 = tmp_registry.register_or_update_template(
        name="KONE Award Template",
        content=content2,
        filename="v2.pptx",
        existing_template_id=res1.template.template_id,
    )

    assert res2.is_new_version is True
    assert res2.template.current_version == 2
    assert len(res2.template.versions) == 2
    assert res2.active_version.version_number == 2
    assert res2.template.versions[0].file_hash != res2.template.versions[1].file_hash


def test_mapping_persistence(tmp_registry):
    content = create_mock_pptx_bytes("Test Mapping")
    res = tmp_registry.register_or_update_template(
        name="Mapping Test Template",
        content=content,
        filename="mapping_test.pptx",
    )

    new_mapping = FieldMappingConfig(
        employee_name=FieldMappingDetail(shape_name="EmployeeName", required=True),
        designation=FieldMappingDetail(shape_name="Designation", required=False),
        branch=FieldMappingDetail(shape_name="Branch", required=False),
        award_name=FieldMappingDetail(shape_name="AwardName", required=False),
    )

    updated_meta = tmp_registry.update_template_mapping(
        template_id=res.template.template_id,
        mapping=new_mapping,
        version_number=1,
    )

    assert updated_meta.versions[0].mapping_config.employee_name.shape_name == "EmployeeName"

    # Verify reloading from disk maintains mapping
    reloaded = tmp_registry.get_template(res.template.template_id)
    assert reloaded.versions[0].mapping_config.employee_name.shape_name == "EmployeeName"


def test_archive_template(tmp_registry):
    content = create_mock_pptx_bytes("Archive Test")
    res = tmp_registry.register_or_update_template(
        name="To Archive",
        content=content,
        filename="archive.pptx",
    )

    archived = tmp_registry.archive_template(res.template.template_id)
    assert archived.is_archived is True

    all_active = tmp_registry.list_templates(include_archived=False)
    assert len(all_active) == 0

    all_with_archived = tmp_registry.list_templates(include_archived=True)
    assert len(all_with_archived) == 1
