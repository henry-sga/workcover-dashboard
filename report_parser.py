"""
Incident report parser — extracts text from uploaded PDF/DOCX files
and matches field labels to pre-fill the New Case wizard.
"""

from __future__ import annotations

import re
import io
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract all text from a .docx file (paragraphs + table cells)."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())

    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                parts.append(" | ".join(row_text))

    return "\n".join(parts)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF using pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Field parsing helpers
# ---------------------------------------------------------------------------

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> str | None:
    """Return the first captured group, or None."""
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _parse_date(raw: str | None) -> str | None:
    """Try to normalise a date string to YYYY-MM-DD."""
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y",
                "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw.strip()


# ---------------------------------------------------------------------------
# Main field extraction
# ---------------------------------------------------------------------------

def _parse_fields_from_text(text: str) -> dict:
    """
    Match common field labels from incident / Register of Injury reports.
    Returns a dict whose keys match the New Case wizard field names.
    """
    fields: dict = {}

    # Employee name
    name = (_find(r"(?:employee|worker|injured person)(?:'s)?\s*(?:full\s*)?name\s*[:\-]\s*(.+)", text)
            or _find(r"name\s+of\s+(?:employee|worker|injured person)\s*[:\-]\s*(.+)", text))
    if name:
        fields["worker_name"] = name.split("\n")[0].strip()

    # Date of birth
    dob = _find(r"(?:date\s+of\s+birth|dob|d\.o\.b)\s*[:\-]\s*(\S+)", text)
    if dob:
        fields["dob"] = _parse_date(dob) or dob

    # Phone
    phone = (_find(r"(?:phone|telephone|contact\s*number|mobile)\s*[:\-]\s*([\d\s\+\(\)]{8,})", text)
             or _find(r"(?:ph|mob)\s*[:\-]\s*([\d\s\+\(\)]{8,})", text))
    if phone:
        fields["phone"] = re.sub(r"\s+", " ", phone).strip()

    # Email
    email = (_find(r"(?:email|e-mail)\s*[:\-]\s*([\w.\-+]+@[\w.\-]+\.\w+)", text)
             or _find(r"([\w.\-+]+@[\w.\-]+\.\w+)", text))
    if email:
        fields["email"] = email.strip()

    # Site / Workplace
    site = (_find(r"(?:workplace|work\s*site|site|location\s+of\s+workplace)\s*[:\-]\s*(.+)", text)
            or _find(r"(?:place\s+of\s+incident)\s*[:\-]\s*(.+)", text))
    if site:
        fields["site"] = site.split("\n")[0].strip()

    # Date of incident / injury
    doi = (_find(r"(?:date\s+of\s+(?:injury|incident|accident))\s*[:\-]\s*(\S+)", text)
           or _find(r"(?:incident\s+date|injury\s+date)\s*[:\-]\s*(\S+)", text))
    if doi:
        fields["date_of_injury"] = _parse_date(doi) or doi

    # What happened / description
    desc = (_find(r"(?:what\s+happened|description\s+of\s+(?:injury|incident|accident)|how\s+(?:did\s+)?(?:the\s+)?(?:injury|incident)\s+occur)\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z])", text, re.IGNORECASE | re.DOTALL)
            or _find(r"(?:what\s+happened|description\s+of\s+(?:injury|incident))\s*[:\-]\s*(.+)", text))
    if desc:
        fields["injury_description"] = desc.strip()

    # Witnesses
    witness = _find(r"(?:witness(?:es)?|witness\s+name)\s*[:\-]\s*(.+)", text)
    if witness:
        fields["witnesses"] = witness.split("\n")[0].strip()

    # Employment type
    emp_type = _find(r"(?:employment\s+(?:type|status|basis))\s*[:\-]\s*(.+)", text)
    if emp_type:
        fields["employment_type"] = emp_type.split("\n")[0].strip()

    # Tenure / length of service
    tenure = _find(r"(?:tenure|length\s+of\s+(?:service|employment))\s*[:\-]\s*(.+)", text)
    if tenure:
        fields["tenure"] = tenure.split("\n")[0].strip()

    # Hours / shift
    shift = (_find(r"(?:shift|hours\s+(?:of\s+work|worked)|roster)\s*[:\-]\s*(.+)", text)
             or _find(r"(?:normal\s+working\s+hours)\s*[:\-]\s*(.+)", text))
    if shift:
        fields["shift_structure"] = shift.split("\n")[0].strip()

    # Nature of injury / body part
    nature = _find(r"(?:nature\s+of\s+injury|type\s+of\s+injury)\s*[:\-]\s*(.+)", text)
    if nature:
        fields["nature_of_injury"] = nature.split("\n")[0].strip()

    body_part = (_find(r"(?:body\s+part|part\s+of\s+body|injured\s+body\s+part)\s*[:\-]\s*(.+)", text)
                 or _find(r"(?:area\s+of\s+injury)\s*[:\-]\s*(.+)", text))
    if body_part:
        fields["body_part"] = body_part.split("\n")[0].strip()

    # Treatment
    treatment = _find(r"(?:treatment|medical\s+treatment|first\s+aid)\s*[:\-]\s*(.+)", text)
    if treatment:
        fields["treatment"] = treatment.split("\n")[0].strip()

    # Entity / employer
    entity = (_find(r"(?:employer|entity|company|business\s+name)\s*[:\-]\s*(.+)", text)
              or _find(r"(?:name\s+of\s+employer)\s*[:\-]\s*(.+)", text))
    if entity:
        fields["entity"] = entity.split("\n")[0].strip()

    # State
    state = _find(r"(?:state|state/territory)\s*[:\-]\s*(VIC|NSW|QLD|TAS|SA|WA|ACT|NT)", text)
    if state:
        fields["state"] = state.upper()

    return fields


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_uploaded_report(file_bytes: bytes, file_type: str) -> dict:
    """
    Extract text from an uploaded file and parse fields.

    Parameters
    ----------
    file_bytes : raw bytes of the uploaded file
    file_type  : one of "pdf", "docx"

    Returns
    -------
    dict mapping wizard field names to extracted values
    """
    if file_type == "docx":
        text = _extract_text_from_docx(file_bytes)
    elif file_type == "pdf":
        text = _extract_text_from_pdf(file_bytes)
    else:
        return {}

    if not text.strip():
        return {}

    return _parse_fields_from_text(text)
