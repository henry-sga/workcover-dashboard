"""
Document generator — produces Register of Injury and other forms as DOCX files.
"""

import io
from datetime import date
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH


def _add_row(table, label: str, value: str):
    """Add a label-value row to a table."""
    row = table.add_row()
    c0, c1 = row.cells
    c0.text = label
    c1.text = value or ""
    for cell in (c0, c1):
        for para in cell.paragraphs:
            para.style.font.size = Pt(10)


def generate_register_of_injury(incident_data: dict) -> bytes:
    """
    Generate a Register of Injury document (DOCX) and return the bytes.

    ``incident_data`` should contain keys like:
        worker_name, dob, email, phone, entity, site, state,
        date_of_injury, injury_description, body_part, nature_of_injury,
        treatment, witnesses, shift_structure, employment_type, tenure
    """
    doc = Document()

    # Title
    title = doc.add_heading("Register of Injury", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(f"Date Generated: {date.today().strftime('%d/%m/%Y')}")

    # --- Part A: Employee / Injured Person Details ---
    doc.add_heading("Part A — Employee / Injured Person Details", level=2)
    table_a = doc.add_table(rows=0, cols=2)
    table_a.style = "Table Grid"
    table_a.alignment = WD_TABLE_ALIGNMENT.CENTER

    _add_row(table_a, "Employee Name", incident_data.get("worker_name", ""))
    _add_row(table_a, "Date of Birth", incident_data.get("dob", ""))
    _add_row(table_a, "Employee Email", incident_data.get("email", ""))
    _add_row(table_a, "Employee Phone", incident_data.get("phone", ""))
    _add_row(table_a, "Employer / Entity", incident_data.get("entity", ""))
    _add_row(table_a, "Workplace / Site", incident_data.get("site", ""))
    _add_row(table_a, "State", incident_data.get("state", ""))
    _add_row(table_a, "Employment Type", incident_data.get("employment_type", ""))
    _add_row(table_a, "Tenure / Length of Service", incident_data.get("tenure", ""))
    _add_row(table_a, "Shift / Hours of Work", incident_data.get("shift_structure", ""))

    # --- Part B: Incident Details ---
    doc.add_heading("Part B — Incident Details", level=2)
    table_b = doc.add_table(rows=0, cols=2)
    table_b.style = "Table Grid"
    table_b.alignment = WD_TABLE_ALIGNMENT.CENTER

    _add_row(table_b, "Date of Injury / Incident", incident_data.get("date_of_injury", ""))
    _add_row(table_b, "Location of Incident", incident_data.get("site", ""))
    _add_row(table_b, "Description (What Happened)", incident_data.get("injury_description", ""))
    _add_row(table_b, "Nature of Injury", incident_data.get("nature_of_injury", ""))
    _add_row(table_b, "Body Part Injured", incident_data.get("body_part", ""))
    _add_row(table_b, "Treatment Given", incident_data.get("treatment", ""))
    _add_row(table_b, "Witness(es)", incident_data.get("witnesses", ""))

    # --- Part C: Declaration ---
    doc.add_heading("Part C — Declaration", level=2)
    doc.add_paragraph(
        "I declare that the information provided above is true and correct "
        "to the best of my knowledge."
    )

    table_c = doc.add_table(rows=0, cols=2)
    table_c.style = "Table Grid"
    table_c.alignment = WD_TABLE_ALIGNMENT.CENTER
    _add_row(table_c, "Employee Signature", "")
    _add_row(table_c, "Date", "")
    _add_row(table_c, "Manager / Supervisor Name", "")
    _add_row(table_c, "Manager Signature", "")
    _add_row(table_c, "Date", "")

    # Write to bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
