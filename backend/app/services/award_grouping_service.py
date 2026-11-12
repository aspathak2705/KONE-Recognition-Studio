import unicodedata
import re
from typing import List, Dict
from app.schemas.photo_matching import EmployeePhotoMatch
from app.schemas.dynamic_presentation import AwardGroup


def normalize_award_category(category_name: str) -> str:
    """
    Normalizes award category string for deterministic grouping.
    Preserves readable title case for presentation while grouping equivalent variations.
    """
    if not category_name:
        return ""
    nfkd = unicodedata.normalize("NFKD", category_name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[_\-\.]+", " ", stripped)
    return " ".join(cleaned.split()).strip()


def group_employees_by_award(
    employees: List[EmployeePhotoMatch]
) -> List[AwardGroup]:
    """
    Groups validated employee records by their award category.
    Requirements:
    1. Deterministic ordering: Preserves order of first appearance or alphabetical.
    2. Zero employee loss or duplication: Every record is mapped into exactly one group.
    3. Retains all employee details & resolved photo assignments.
    """
    groups_dict: Dict[str, AwardGroup] = {}
    display_name_map: Dict[str, str] = {}

    for emp in employees:
        raw_award = (emp.award_name or "").strip()
        if not raw_award:
            raise ValueError(f"Employee '{emp.employee_name}' has missing or blank award name.")

        norm_key = normalize_award_category(raw_award).lower()
        if norm_key not in groups_dict:
            display_name = raw_award
            groups_dict[norm_key] = AwardGroup(
                award_name=display_name,
                normalized_award_name=norm_key,
                employee_count=0,
                employees=[],
            )
            display_name_map[norm_key] = display_name

        groups_dict[norm_key].employees.append(emp)
        groups_dict[norm_key].employee_count += 1

    # Deterministic alphabetical ordering by normalized award category
    sorted_groups = sorted(groups_dict.values(), key=lambda g: g.normalized_award_name)
    return sorted_groups
