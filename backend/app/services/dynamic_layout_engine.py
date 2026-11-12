from typing import List, Tuple
from app.schemas.dynamic_presentation import DynamicLayoutConfig

# 16:9 widescreen presentation dimensions
SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5

HEADER_HEIGHT_IN = 1.6
FOOTER_MARGIN_IN = 0.5
SIDE_MARGIN_IN = 0.8


def calculate_optimal_slide_layout(
    employee_count_in_slide: int,
    max_name_len: int = 20,
    max_meta_len: int = 30,
) -> DynamicLayoutConfig:
    """
    Dynamically computes optimal grid layout (columns, rows, card dimensions)
    to maximize readability and fit without clipping or overflow.
    Candidate layout grid patterns:
    - 1 card: centered hero card
    - 2 cards: 1x2 or 2x1
    - 3 cards: 3x1
    - 4 cards: 2x2 or 4x1
    - 5-6 cards: 3x2
    - 7-8 cards: 4x2
    - 9-10 cards: 5x2
    - 11-12 cards: 4x3 or 6x2
    """
    avail_width = SLIDE_WIDTH_IN - (SIDE_MARGIN_IN * 2)
    avail_height = SLIDE_HEIGHT_IN - HEADER_HEIGHT_IN - FOOTER_MARGIN_IN

    # Determine optimal grid dimensions
    if employee_count_in_slide <= 1:
        cols, rows = 1, 1
    elif employee_count_in_slide == 2:
        cols, rows = 2, 1
    elif employee_count_in_slide == 3:
        cols, rows = 3, 1
    elif employee_count_in_slide == 4:
        cols, rows = 2, 2
    elif employee_count_in_slide in (5, 6):
        cols, rows = 3, 2
    elif employee_count_in_slide in (7, 8):
        cols, rows = 4, 2
    elif employee_count_in_slide in (9, 10):
        cols, rows = 5, 2
    else:
        # Default maximum density: 4 cols x 3 rows = 12 cards per slide
        cols, rows = 4, 3

    # Calculate gaps and card dimensions
    gap_x = 0.35 if cols > 2 else 0.5
    gap_y = 0.3 if rows > 1 else 0.4

    card_width = (avail_width - (gap_x * (cols - 1))) / cols
    card_height = (avail_height - (gap_y * (rows - 1))) / rows

    # Bound card size to keep elegant proportions
    if cols == 1 and rows == 1:
        card_width = min(card_width, 5.0)
        card_height = min(card_height, 4.0)

    # Determine photo size and font sizing based on card height and column density
    if rows == 1:
        image_size = min(card_width * 0.45, card_height * 0.55, 2.2)
        name_size = 18.0
        meta_size = 13.0
    elif rows == 2:
        image_size = min(card_width * 0.4, card_height * 0.45, 1.4)
        name_size = 13.0
        meta_size = 10.5
    else:
        image_size = min(card_width * 0.35, card_height * 0.4, 1.1)
        name_size = 11.0
        meta_size = 9.0

    # Readability safety adjustments for unusually long text
    if max_name_len > 25:
        name_size = max(name_size - 1.5, 9.5)
    if max_meta_len > 35:
        meta_size = max(meta_size - 1.0, 8.5)

    # Center grid horizontally in available slide width
    total_grid_w = (cols * card_width) + ((cols - 1) * gap_x)
    margin_left = SIDE_MARGIN_IN + (avail_width - total_grid_w) / 2.0
    margin_top = HEADER_HEIGHT_IN + 0.1

    return DynamicLayoutConfig(
        columns=cols,
        rows=rows,
        max_cards_per_slide=cols * rows,
        card_width_in=round(card_width, 3),
        card_height_in=round(card_height, 3),
        margin_left_in=round(margin_left, 3),
        margin_top_in=round(margin_top, 3),
        gap_x_in=round(gap_x, 3),
        gap_y_in=round(gap_y, 3),
        image_size_in=round(image_size, 3),
        name_font_size_pt=name_size,
        meta_font_size_pt=meta_size,
    )


def paginate_award_group(
    total_in_group: int,
    max_density_per_slide: int = 8,
) -> List[int]:
    """
    Determines balanced card counts per slide for an award group.
    Avoids trailing lone orphan cards (e.g. 9 employees -> 5 on slide 1, 4 on slide 2 instead of 8 and 1).
    """
    if total_in_group <= max_density_per_slide:
        return [total_in_group]

    num_slides = (total_in_group + max_density_per_slide - 1) // max_density_per_slide
    base_count = total_in_group // num_slides
    remainder = total_in_group % num_slides

    counts = []
    for i in range(num_slides):
        count = base_count + (1 if i < remainder else 0)
        counts.append(count)
    return counts
