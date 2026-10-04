from pathlib import Path
from app.services.template_registry_service import template_registry

downloads_dir = Path(r"C:\Users\athar\Downloads")
q4_path = downloads_dir / "Q4 R&R 2025.pptx"
nj_path = downloads_dir / "New Joiner Template.pptx"

print("Q4 R&R 2025 exists:", q4_path.exists())
print("New Joiner Template exists:", nj_path.exists())

if q4_path.exists():
    with open(q4_path, "rb") as f:
        content = f.read()
    res_q4 = template_registry.register_or_update_template("Q4 R&R 2025", content, "Q4 R&R 2025.pptx")
    print("Registered Q4 template:", res_q4.template.name, "v", res_q4.active_version.version_number, "ID:", res_q4.template.template_id, "Hash:", res_q4.active_version.file_hash)

if nj_path.exists():
    with open(nj_path, "rb") as f:
        content = f.read()
    res_nj = template_registry.register_or_update_template("New Joiner Template", content, "New Joiner Template.pptx")
    print("Registered New Joiner template:", res_nj.template.name, "v", res_nj.active_version.version_number, "ID:", res_nj.template.template_id, "Hash:", res_nj.active_version.file_hash)
