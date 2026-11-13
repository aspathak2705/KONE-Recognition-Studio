# 20-Employee End-to-End Acceptance Test Dataset

## Overview
This directory contains a dedicated, isolated test dataset for validating the complete KONE Recognition Studio dynamic presentation generation workflow.

## Structure
- `employees_20.xlsx`: Excel workbook containing 20 unique synthetic employee records across 3 award categories.
- `employee_photos/`: Directory containing exactly 20 distinct synthetic portrait images named corresponding to employee names (`<Employee Name>.jpg`).

## Dataset Distribution
- **Star Performer**: 8 employees
- **Customer Excellence**: 7 employees
- **Innovation Champion**: 5 employees
- **Total Employees**: 20

## Verification Objectives
1. Template-free workflow execution (Excel + Photos -> Match -> Award Groups -> Dynamic PPTX).
2. Proper award category grouping and dynamic slide pagination.
3. Native shape and picture embedding in 16:9 PowerPoint widescreen format.
4. Microsoft PowerPoint COM preview rendering and delivery verification.
