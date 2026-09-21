# Template Architecture & Inspection Guidelines

This directory stores master PowerPoint templates (e.g. KONE newspaper-style template) uploaded by HR users.

## Inspection vs Generation Boundary (Phase 1 vs Phase 2)

- **Phase 1 Inspection**: Reads `.pptx` presentation structure using `python-pptx` without modifying shapes, slides, or underlying layouts.
- **Phase 2 Generation**: Will clone slide layouts, substitute dynamic text frames, and generate downloadable editable `.pptx` files.

## Phase 2 Dependency Checklist

Before Phase 2 PowerPoint generation can be implemented, the following layout decisions must be aligned:

1. **Card Layout Structure**: Which slide layout or shapes represent an employee recognition card?
2. **Capacity per Slide**: How many recognition cards fit on a single newspaper page?
3. **Multi-Slide Spillovers**: How should the system handle batches exceeding single-slide capacity?
4. **Font Overflow & Wrapping**: What maximum character limits apply to long employee or award names?
5. **Manual Photo Alignment**: How will HR manually insert photos into generated picture frames?
