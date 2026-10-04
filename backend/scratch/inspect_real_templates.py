import json
from pathlib import Path
from app.schemas.template import TemplateInspectionResponse
from app.services.template_registry_service import template_registry

q4_meta = template_registry.get_template("f27b8666ba9d4dd0bd8d383581ba31ba")
nj_meta = template_registry.get_template("046f2871d4ee4c53b2ee3d469a795432")

q4_dir = template_registry._get_template_dir("f27b8666ba9d4dd0bd8d383581ba31ba")
nj_dir = template_registry._get_template_dir("046f2871d4ee4c53b2ee3d469a795432")

with open(q4_dir / "inspection_v1.json", "r", encoding="utf-8") as f:
    q4_inspection = TemplateInspectionResponse(**json.load(f))

with open(nj_dir / "inspection_v1.json", "r", encoding="utf-8") as f:
    nj_inspection = TemplateInspectionResponse(**json.load(f))

print("=== Q4 R&R 2025 INSPECTION SUMMARY ===")
print("Slide Count:", q4_inspection.slide_count)
for s in q4_inspection.slides:
    print(f"Slide {s.slide_number}: type={s.layout_model.slide_type if s.layout_model else 'N/A'}, capacity={s.layout_model.capacity if s.layout_model else 'N/A'}, text_shapes={len(s.text_shapes)}, image_shapes={len(s.image_shapes)}")
    for ts in s.text_shapes:
        if ts.text:
            print(f"   [TextShape] name='{ts.shape_name}', text='{ts.text[:40]}'")
    for img in s.image_shapes:
        print(f"   [ImageRegion] name='{img.shape_name}', sample_photo={img.is_sample_photo}")

print("\n=== NEW JOINER TEMPLATE INSPECTION SUMMARY ===")
print("Slide Count:", nj_inspection.slide_count)
for s in nj_inspection.slides:
    print(f"Slide {s.slide_number}: type={s.layout_model.slide_type if s.layout_model else 'N/A'}, capacity={s.layout_model.capacity if s.layout_model else 'N/A'}, text_shapes={len(s.text_shapes)}, image_shapes={len(s.image_shapes)}")
    for ts in s.text_shapes:
        if ts.text:
            print(f"   [TextShape] name='{ts.shape_name}', text='{ts.text[:40]}'")
    for img in s.image_shapes:
        print(f"   [ImageRegion] name='{img.shape_name}', sample_photo={img.is_sample_photo}")
