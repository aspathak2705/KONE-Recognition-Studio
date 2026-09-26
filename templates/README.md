# Template Architecture & Generation Guidelines

This directory stores master PowerPoint templates (`.pptx`) uploaded by HR users and configuration guidelines for Phase 2 generation.

## Field Mapping Contract

Each field in the canonical recognition schema must map to a valid shape name on slide #1 of the master template:

- `employee_name` -> Target text shape name (e.g., `EmployeeName`)
- `designation` -> Target text shape name (e.g., `Designation`)
- `branch` -> Target text shape name (e.g., `Branch`)
- `award_name` -> Target text shape name (e.g., `AwardName`)

## Generation & Layout Cloning Rules

1. **Slide Cloning**: The generator clones slide #1 for each employee recognition record in the Excel dataset.
2. **Formatting Preservation**: Font family, font size, font color (RGB), bold/italic attributes, and text alignment are copied from the template's initial run formatting.
3. **Template Preservation**: Master template files in `storage/uploads/templates/` remain strictly read-only and are never modified.
4. **Output Storage**: Generated presentations are written to `storage/generated/<generation_id>.pptx` with a unique UUID file identifier.
5. **Manual Photo Alignment**: Post-generation HR activity for pasting employee photo assets into the generated presentation.
