---
name: bom-boq-exporters
description: openpyxl BOM (.xlsx) and python-docx BOQ (.docx) export conventions — column order, blank pricing, compliance text
---

# BOM/BOQ Export Conventions

## BOM Export (.xlsx via openpyxl)

### Column Order (§8.4, §3 Phase 2 step 3)

| # | Column Header | Data Source | Notes |
|---|---|---|---|
| 1 | S.No. | Auto-increment | Starting from 1 |
| 2 | OEM | Products.OEM_Name | |
| 3 | Product Name | Products.Product_Name | |
| 4 | Product Category | Products.Product_Category | |
| 5 | Model/Part Reference | Products.Product_ID | |
| 6 | Quantity | Engineer input (grid) | Integer, 1–99,999 |
| 7 | Licensing Model | Product_Commercial.Licensing_Model | |
| 8 | License Term | Engineer selection | From grid dropdown |
| 9 | Licensing Unit | Product_Commercial.Licensing_Unit | |
| 10 | Deployment Model | Products.Deployment_Model | |
| 11 | Support Tier | Engineer selection | From grid dropdown |
| 12 | Unit Price | **BLANK** | Header: "Unit Price — To be filled by Sales" |
| 13 | Total Price | **BLANK** | Header: "Total Price — To be filled by Sales" |
| 14 | Remarks | Optional engineer input | |

### Implementation Pattern

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def export_bom(items, output_path, customer_name=""):
    wb = Workbook()
    ws = wb.active
    ws.title = "Bill of Materials"
    
    # Row 1: Disclaimer
    ws.merge_cells("A1:N1")
    ws["A1"] = "DRAFT — PRICING NOT INCLUDED — FOR INTERNAL USE ONLY"
    ws["A1"].font = Font(bold=True, color="FF0000", size=12)
    ws["A1"].alignment = Alignment(horizontal="center")
    
    # Row 2: Company header
    ws.merge_cells("A2:N2")
    ws["A2"] = "iValue InfoSolutions — Bill of Materials"
    ws["A2"].font = Font(bold=True, size=14)
    
    # Row 3: Customer info (if provided)
    if customer_name:
        ws["A3"] = f"Customer: {customer_name}"
    
    # Row 4: Column headers
    headers = [
        "S.No.", "OEM", "Product Name", "Product Category",
        "Model/Part Reference", "Quantity", "Licensing Model",
        "License Term", "Licensing Unit", "Deployment Model",
        "Support Tier",
        "Unit Price — To be filled by Sales",
        "Total Price — To be filled by Sales",
        "Remarks"
    ]
    header_row = 4
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="0F172A", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    
    # Data rows
    for i, item in enumerate(items, 1):
        row = header_row + i
        ws.cell(row=row, column=1, value=i)  # S.No.
        ws.cell(row=row, column=2, value=item.oem)
        ws.cell(row=row, column=3, value=item.product_name)
        ws.cell(row=row, column=4, value=item.product_category)
        ws.cell(row=row, column=5, value=item.product_id)
        ws.cell(row=row, column=6, value=item.quantity)
        ws.cell(row=row, column=7, value=item.licensing_model or "TBD — Consult Sales")
        ws.cell(row=row, column=8, value=item.license_term)
        ws.cell(row=row, column=9, value=item.licensing_unit or "TBD — Consult Sales")
        ws.cell(row=row, column=10, value=item.deployment_model)
        ws.cell(row=row, column=11, value=item.support_tier)
        # Columns 12-13: ALWAYS BLANK (pricing)
        ws.cell(row=row, column=14, value=item.remarks)
    
    # Auto-size columns
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_length + 4, 40)
    
    wb.save(output_path)
```

### CRITICAL: Pricing Columns
- Columns 12 and 13 must **ALWAYS** be blank cells — no values, no formulas, no estimates.
- Headers explicitly state "To be filled by Sales".
- Missing licensing fields: fill with "TBD — Consult Sales" (§10.5).

## BOQ Export (.docx via python-docx)

### Document Structure (§8.4)

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def export_boq(items, output_path, customer_name, project_reference, prepared_by):
    doc = Document()
    
    # --- Header / Letterhead ---
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run("iValue InfoSolutions")
    run.font.size = Pt(18)
    run.font.bold = True
    
    # --- Watermark text (header section) ---
    section = doc.sections[0]
    header = section.header
    hp = header.paragraphs[0]
    hp.text = "DRAFT — PRICING NOT INCLUDED"
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.style.font.color.rgb = RGBColor(200, 200, 200)
    
    # --- Metadata ---
    doc.add_paragraph(f"Customer: {customer_name}")
    doc.add_paragraph(f"Project Reference: {project_reference}")
    doc.add_paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    doc.add_paragraph(f"Prepared By: {prepared_by}")
    doc.add_paragraph("")
    
    # --- Line Items Table ---
    table = doc.add_table(rows=1, cols=14, style="Table Grid")
    # ... (same column structure as BOM)
    # Price cells: BLANK
    
    # --- Footer ---
    doc.add_paragraph("")
    footer_para = doc.add_paragraph("Pricing to be completed by iValue Sales Team")
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Document generated by iValue PRISM v3.4 — {datetime.now().isoformat()}")
    
    doc.save(output_path)
```

### File Naming Convention (§8.1.15)
- BOM: `iValue_BOM_<PrimaryOEM>_<YYYYMMDD>.xlsx`
- BOQ: `iValue_BOQ_<PrimaryOEM>_<CustomerName>_<YYYYMMDD>.docx`

### Error Handling (§10.5)
- Missing fields → fill with "TBD — Consult Sales"
- Template rendering failure → fall back to simple CSV export
- Disk full → catch IOError/OSError, show user message, no partial file
