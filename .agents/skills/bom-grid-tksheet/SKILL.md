---
name: bom-grid-tksheet
description: tksheet DataGrid implementation for BOM/BOQ export panel — dark-theme styling, embedded spinbox/dropdown editors, strict column alignment
---

# BOM Grid via tksheet

## Why tksheet (not hand-rolled CTkFrames)
SRS §9.5 explicitly rejects hand-rolled Tkinter nested-frame grids due to column misalignment drift, scroll sync failures, and high widget-tree overhead. `tksheet` (v7.0.0+) provides a virtualized canvas with strict column alignment.

## Installation
Already in `requirements.txt`: `tksheet>=7.0.0`

## Basic Setup Pattern

```python
import tksheet

class ExportControlPanel(customtkinter.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.sheet = tksheet.Sheet(
            self,
            headers=["Product Name", "Category", "Qty", "License Term", "Support Tier"],
            show_x_scrollbar=False,
            show_y_scrollbar=True,
            height=250,
        )
        self.sheet.pack(fill="both", expand=True, padx=8, pady=8)
        self.sheet.enable_bindings()
```

## Dark-Theme Styling (from §8.1.5 item 5)

```python
def apply_dark_theme(sheet: tksheet.Sheet):
    sheet.set_options(
        # Header
        header_bg="#0F172A",
        header_fg="#F8FAFC",
        header_font=("Segoe UI", 11, "bold"),
        # Alternating rows
        odd_row_bg="#131F37",
        even_row_bg="#0D1527",
        # Text
        table_fg="#F8FAFC",
        table_font=("Segoe UI", 11, "normal"),
        # Active cell accent
        table_selected_cells_border_fg="#0EA5E9",
        table_selected_cells_bg="#1E293B",
        # Frame
        frame_bg="#0B1120",
        table_bg="#0D1527",
    )

def apply_light_theme(sheet: tksheet.Sheet):
    sheet.set_options(
        header_bg="#E2E8F0",
        header_fg="#0F172A",
        header_font=("Segoe UI", 11, "bold"),
        odd_row_bg="#FFFFFF",
        even_row_bg="#F8FAFC",
        table_fg="#0F172A",
        table_font=("Segoe UI", 11, "normal"),
        table_selected_cells_border_fg="#0EA5E9",
        table_selected_cells_bg="#E0F2FE",
        frame_bg="#F1F5F9",
        table_bg="#FFFFFF",
    )
```

## Embedded In-Cell Controls (§8.1.5 item 5)

### Quantity Column — Numeric Spinbox
```python
# Validate quantity: integers 1–99,999
sheet.set_cell_data(row, qty_col, 1)  # default
# Use cell validation callback:
def validate_qty(event):
    try:
        val = int(event.value)
        if 1 <= val <= 99999:
            return val
    except (ValueError, TypeError):
        pass
    return event.previous_value  # reject invalid

sheet.extra_bindings([("end_edit_cell", validate_qty)])
```

### License Term Column — Dropdown
```python
LICENSE_TERMS = ["1-Year", "3-Year", "5-Year", "Perpetual"]
sheet.set_dropdown_values(
    r=row, c=license_col,
    values=LICENSE_TERMS,
    set_value="1-Year"
)
```

### Support Tier Column — Dropdown
```python
SUPPORT_TIERS = ["Standard", "24x7 Enterprise", "Mission Critical"]
sheet.set_dropdown_values(
    r=row, c=support_col,
    values=SUPPORT_TIERS,
    set_value="Standard"
)
```

## Reading Grid Data for Export
```python
def get_bom_items(self) -> list:
    items = []
    for row in range(self.sheet.get_total_rows()):
        row_data = self.sheet.get_row_data(row)
        items.append(BomItem(
            product_id=row_data[0],  # hidden or mapped
            quantity=int(row_data[2]),
            license_term=row_data[3],
            support_tier=row_data[4],
        ))
    return items
```

## Compliance Warning Banner
Always display above the grid:
```
"[!] Pricing is intentionally omitted and must be completed by Sales per iValue commercial policy."
```

## Regression Guard (§12.8)
After any UI or theme change, verify:
1. Column headers and cell borders maintain strict vertical alignment across 1 row vs. 10+ rows
2. Grid remains responsive at minimum window size (1024×640)
3. Embedded spinbox and dropdowns work in both dark and light mode
