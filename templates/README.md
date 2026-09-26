# KONE Master PowerPoint Template Documentation

## Overview

KONE Recognition Studio uses reusable registered master PowerPoint (`.pptx`) templates stored in the **Template Registry**.

---

## Template Registry & Versioning Architecture

Master PowerPoint templates are persistent, versioned assets. Inspection and field shape mapping occur **ONCE per template version**.

### Lifecycle

```text
Upload PPTX
    ↓
Calculate SHA-256 Hash
    ↓
Check Existing Hashes (Reuse if identical binary)
    ↓
Inspect Slide Structure (python-pptx)
    ↓
Configure Shape Field Mapping (employee_name, designation, branch, award_name)
    ↓
Save Configuration & Master PPTX (storage/templates/<template_id>/)
    ↓
Reuse across recurring HR recognition cycles (NO re-upload required)
```

---

## Storage Layout

```text
storage/templates/<template_id>/
├── template.json            # Master metadata (name, versions, readiness status)
├── master_v1.pptx           # Preserved PowerPoint binary for Version 1
├── inspection_v1.json       # Inspected shape structure for Version 1
└── mapping_v1.json          # Perserved field shape mapping for Version 1
```

---

## Canonical Field Mapping Rules

1. **`employee_name`**: Primary title/header shape or text frame containing recipient full name.
2. **`designation`**: Subtitle or body text frame for employee designation/role.
3. **`branch`**: Secondary text frame specifying KONE branch location.
4. **`award_name`**: Badge text frame specifying recognition award title.
