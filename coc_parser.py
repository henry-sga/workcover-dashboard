"""
COC (Certificate of Capacity) parser — extracts fields from uploaded or
scanned COC PDFs using OCR (tesseract) and regex matching.

Supports:
  - NSW SIRA "Certificate of capacity / certificate of fitness"
  - VIC TAC/WorkSafe "Certificate of Capacity"
  - QLD WorkCover "Workers' compensation medical certificate"
  - Fallback filename-based date extraction
"""

from __future__ import annotations

import re
import os
import io
from datetime import datetime, date
from typing import Optional


# ---------------------------------------------------------------------------
# OCR text extraction
# ---------------------------------------------------------------------------

def _extract_text_from_coc_pdf(file_bytes: bytes) -> str:
    """Extract text from a scanned COC PDF using OCR."""
    from pdf2image import convert_from_bytes
    import pytesseract

    images = convert_from_bytes(file_bytes, dpi=250)
    text_parts = []
    for img in images:
        text = pytesseract.image_to_string(img)
        if text.strip():
            text_parts.append(text.strip())
    return "\n\n".join(text_parts)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_au_date(raw: str | None) -> str | None:
    """Parse an Australian-format date string to YYYY-MM-DD."""
    if not raw:
        return None
    raw = raw.strip().replace(" ", "")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y",
                "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _find(pattern: str, text: str, flags=re.IGNORECASE) -> str | None:
    """Return the first captured group, or None."""
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _find_all_dates(text: str) -> list[str]:
    """Find all DD/MM/YYYY dates in text."""
    return re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)


# ---------------------------------------------------------------------------
# Template detection
# ---------------------------------------------------------------------------

def _detect_template(text: str) -> str:
    """Detect which state COC template the text matches."""
    text_lower = text.lower()
    if "sira" in text_lower or "state insurance regulatory authority" in text_lower:
        return "NSW_SIRA"
    if "tac" in text_lower or "worksafe" in text_lower or "transport accident" in text_lower:
        return "VIC_TAC"
    if "queensland" in text_lower or "qcomp" in text_lower or "workcover queensland" in text_lower:
        return "QLD"
    # Try secondary signals
    if "certificate of capacity" in text_lower and "certificate of fitness" in text_lower:
        return "NSW_SIRA"
    if "certificate of capacity" in text_lower and ("worker first name" in text_lower or "worker last name" in text_lower):
        return "VIC_TAC"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# NSW SIRA parser
# ---------------------------------------------------------------------------

def _parse_nsw_sira(text: str) -> dict:
    """Parse NSW SIRA Certificate of Capacity / Certificate of Fitness."""
    fields: dict = {}

    # Worker name
    first = _find(r'First name\s*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    last = _find(r'Last name\s*\n\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', text)
    if first and last:
        fields["worker_name"] = f"{first} {last}"
    elif first:
        fields["worker_name"] = first

    # Claim number — appears before Medicare number on the same line or nearby
    # Try specific "Claim number\nVALUE" pattern first
    claim = _find(r'Claim number\s*\n\s*(\d{5,})', text)
    if not claim:
        # Try on same line after "Claim number"
        claim = _find(r'Claim number\s*[:\s]+(\d{5,})', text)
    if claim:
        fields["claim_number"] = claim.strip()

    # Capacity for work section
    if re.search(r'is fit for pre[- ]?injury (?:duties|work)', text, re.IGNORECASE):
        # Check if this option is actually ticked (near checkbox marker)
        if re.search(r'(?:\[?[xX✓]\]?|☑)\s*is fit for pre', text, re.IGNORECASE):
            fields["capacity"] = "Full Capacity"

    # "has capacity for some type of work from DATE to DATE"
    m = re.search(
        r'has capacity for some type of work from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+[\[|\s]*(\d{1,2}/\d{1,2}/\d{4})',
        text, re.IGNORECASE
    )
    if m:
        fields["capacity"] = "Modified Duties"
        fields["cert_from"] = _parse_au_date(m.group(1))
        fields["cert_to"] = _parse_au_date(m.group(2))

    # hours/day and days/week
    hrs = _find(r'for\s+(\d{1,2}(?:\s*-\s*\d{1,2})?)\s+hours?/day', text)
    days = _find(r'(\d{1,2})\s+days?/week', text)
    if hrs:
        # Take the first number if it's a range like "8-10"
        fields["hours_per_day"] = float(hrs.split("-")[0].strip())
    if days:
        fields["days_per_week"] = int(days)

    # "has no current work capacity" / "has no current capacity"
    m2 = re.search(
        r'has no (?:current )?(?:work )?capaci\w*\s+(?:for any (?:employment|work)\s+)?from\s+[\[|\s]*(\d{1,2}/\d{1,2}/\d{4})\s+.*?to\s+[\[|\s]*(\d{1,2}/\d{1,2}/\d{4})',
        text, re.IGNORECASE
    )
    if m2 and "capacity" not in fields:
        fields["capacity"] = "No Capacity"
        fields["cert_from"] = _parse_au_date(m2.group(1))
        fields["cert_to"] = _parse_au_date(m2.group(2))

    # Next review date
    review = _find(r'Next review date\s*[\(\[]?(?:DD/MM/YYYY)?[\)\]]?\s*[\n|:]*\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if review:
        fields["next_review"] = _parse_au_date(review)

    # Diagnosis
    diag = _find(r'Diagnosis of work related.*?\n\s*(.+?)(?:\n|$)', text)
    if diag:
        fields["diagnosis"] = diag.strip()

    return fields


# ---------------------------------------------------------------------------
# VIC TAC/WorkSafe parser
# ---------------------------------------------------------------------------

def _parse_vic_tac(text: str) -> dict:
    """Parse VIC TAC/WorkSafe Certificate of Capacity."""
    fields: dict = {}

    # Worker name — VIC form uses "Worker First Name" / "Worker Last Name"
    first = _find(r'Worker First Name\s*\n\s*([A-Z][A-Za-z\s]+?)(?:\n|Claim|Date|$)', text)
    if not first:
        first = _find(r'Worker First Name\s*\n\s*(.+?)(?:\n)', text)
    last = _find(r'Worker Last Name\s*\n?\s*(?:not known\)?)?\s*\n?\s*(?:Date of (?:Birth|Injury))?\s*\n?\s*([A-Z][A-Za-z]+)', text)
    if not last:
        last = _find(r'Worker Last Name\s*\n\s*(.+?)(?:\n)', text)
    # Clean up — remove anything that looks like a label
    if first:
        first = re.sub(r'(?:Claim|Date|Worker).*', '', first, flags=re.IGNORECASE).strip()
    if last:
        last = re.sub(r'(?:Date|Worker|not known).*', '', last, flags=re.IGNORECASE).strip()
    if first and last and len(first) > 1 and len(last) > 1:
        fields["worker_name"] = f"{first} {last}"

    # Claim number
    claim = _find(r'Claim Number\s*(?:\(if known\))?\s*\n?\s*([A-Z0-9\s\+]{5,}?)(?:\n|$)', text)
    if claim:
        cleaned = re.sub(r'[^A-Z0-9]', '', claim.upper()).strip()
        if len(cleaned) >= 5:
            fields["claim_number"] = cleaned

    # Capacity - multiple patterns (OCR can be inconsistent)
    # "Have No capacity" - with checkbox marker or just text
    m = re.search(
        r'[Hh]ave [Nn]o capacity for (?:any )?employment from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})',
        text
    )
    if not m:
        m = re.search(
            r'No capacity for employment from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})',
            text
        )
    if m:
        fields["capacity"] = "No Capacity"
        fields["cert_from"] = _parse_au_date(m.group(1))
        fields["cert_to"] = _parse_au_date(m.group(2))

    # "Have a capacity for suitable employment from DATE to DATE"
    m2 = re.search(
        r'[Hh]ave a capacity for suitable employment from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})',
        text
    )
    if m2:
        fields["capacity"] = "Modified Duties"
        fields["cert_from"] = _parse_au_date(m2.group(1))
        fields["cert_to"] = _parse_au_date(m2.group(2))

    # "Have a capacity for pre-injury employment from DATE"
    m3 = re.search(
        r'[Hh]ave a capacity for pre[- ]?injury employment from\s+(\d{1,2}/\d{1,2}/\d{4})',
        text
    )
    if m3:
        fields["capacity"] = "Full Capacity"
        fields["cert_from"] = _parse_au_date(m3.group(1))

    # Diagnosis
    diag = _find(r'Clinical Diagnosis.*?is:\s*\n?\s*(.+?)(?:\n\n|\n[0-9])', text, re.IGNORECASE | re.DOTALL)
    if diag:
        fields["diagnosis"] = diag.strip().split("\n")[0].strip()

    return fields


# ---------------------------------------------------------------------------
# QLD WorkCover parser
# ---------------------------------------------------------------------------

def _parse_qld(text: str) -> dict:
    """Parse QLD WorkCover Workers' compensation medical certificate."""
    fields: dict = {}

    # QLD forms are often rotated/sideways so OCR is less reliable
    # Try to extract key fields

    # Worker name - look for surname/given names pattern
    surname = _find(r'\(surname\)\s*(.+?)(?:\n|I attended)', text)
    given = _find(r'I attended to \(given names\)\s*(.+?)(?:\n|$)', text)
    if not given:
        given = _find(r'given names?\)?\s*(.+?)(?:\n|$)', text)
    if surname and given:
        fields["worker_name"] = f"{given.strip()} {surname.strip()}"
    elif surname:
        fields["worker_name"] = surname.strip()

    # No capacity / suitable duties / normal duties
    m = re.search(
        r'No capacity for any type.*?from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})',
        text, re.IGNORECASE
    )
    if m:
        fields["capacity"] = "No Capacity"
        fields["cert_from"] = _parse_au_date(m.group(1))
        fields["cert_to"] = _parse_au_date(m.group(2))

    m2 = re.search(
        r'(?:suitable|some form of work) duties?\s+from\s+(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})',
        text, re.IGNORECASE
    )
    if m2 and "capacity" not in fields:
        fields["capacity"] = "Modified Duties"
        fields["cert_from"] = _parse_au_date(m2.group(1))
        fields["cert_to"] = _parse_au_date(m2.group(2))

    return fields


# ---------------------------------------------------------------------------
# Filename date extraction (fallback)
# ---------------------------------------------------------------------------

def _extract_dates_from_filename(filename: str) -> dict:
    """
    Try to extract from/to dates from COC filename patterns:
      COC 14.01-28.01.pdf
      COC 31.01 - 28.02.pdf
      COC 16.12-29.12.pdf
    """
    fields: dict = {}
    # Pattern: DD.MM - DD.MM or DD.MM-DD.MM (2-digit day.month)
    m = re.search(r'(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})', filename)
    if m:
        d1, m1, d2, m2 = m.groups()
        # Guess the year — use current year, unless from month > to month (spans year boundary)
        year = date.today().year
        try:
            from_date = date(year, int(m1), int(d1))
            to_date = date(year, int(m2), int(d2))
            if to_date < from_date:
                # Might span year boundary — from is previous year
                from_date = date(year - 1, int(m1), int(d1))
            fields["cert_from"] = from_date.isoformat()
            fields["cert_to"] = to_date.isoformat()
        except ValueError:
            pass
    return fields


# ---------------------------------------------------------------------------
# Worker matching
# ---------------------------------------------------------------------------

def match_worker_from_text(text: str, worker_names: list[str]) -> str | None:
    """
    Try to match a worker name from the OCR text against the list of known
    workers in the database. Uses fuzzy substring matching.
    """
    text_upper = text.upper()
    best_match = None
    best_score = 0

    for name in worker_names:
        parts = name.upper().split()
        # Check if last name appears in text
        if len(parts) >= 2:
            last = parts[-1]
            first = parts[0]
            # Full name match (best)
            if name.upper() in text_upper:
                return name
            # Last name match
            if last in text_upper and len(last) > 2:
                score = 2
                # First name also matches
                if first in text_upper:
                    score = 3
                if score > best_score:
                    best_score = score
                    best_match = name
        elif name.upper() in text_upper:
            return name

    return best_match if best_score >= 2 else None


def match_worker_from_path(file_path: str, worker_names: list[str]) -> str | None:
    """Try to match worker from the folder path."""
    # Active Cases/[Worker Name]/Medical/COC/...
    parts = file_path.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part.lower() in ("active cases",):
            if i + 1 < len(parts):
                folder_name = parts[i + 1]
                # Try to match folder name against worker names
                folder_upper = folder_name.upper()
                for name in worker_names:
                    name_upper = name.upper()
                    # Direct match or folder contains the name
                    if name_upper in folder_upper or folder_upper in name_upper:
                        return name
                    # Match on last name
                    last = name_upper.split()[-1] if name_upper.split() else ""
                    if last and last in folder_upper:
                        return name
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_coc_pdf(file_bytes: bytes, filename: str = "") -> dict:
    """
    Parse a COC PDF and extract certificate fields.

    Returns dict with keys:
        worker_name, claim_number, capacity, cert_from, cert_to,
        hours_per_day, days_per_week, next_review, diagnosis, template
    """
    # Step 1: OCR extraction
    try:
        text = _extract_text_from_coc_pdf(file_bytes)
    except Exception:
        text = ""

    if not text.strip():
        # Fallback: try filename dates only
        fields = _extract_dates_from_filename(filename)
        fields["_raw_text"] = ""
        fields["template"] = "UNKNOWN"
        fields["_ocr_failed"] = True
        return fields

    # Step 2: Detect template
    template = _detect_template(text)

    # Step 3: Parse based on template
    if template == "NSW_SIRA":
        fields = _parse_nsw_sira(text)
    elif template == "VIC_TAC":
        fields = _parse_vic_tac(text)
    elif template == "QLD":
        fields = _parse_qld(text)
    else:
        # Generic fallback — try all parsers and merge
        fields = {}
        for parser in (_parse_nsw_sira, _parse_vic_tac, _parse_qld):
            result = parser(text)
            for k, v in result.items():
                if k not in fields and v:
                    fields[k] = v

    fields["template"] = template
    fields["_raw_text"] = text

    # Step 4: If dates not found from OCR, try filename
    if "cert_from" not in fields or "cert_to" not in fields:
        fn_dates = _extract_dates_from_filename(filename)
        if "cert_from" not in fields and "cert_from" in fn_dates:
            fields["cert_from"] = fn_dates["cert_from"]
        if "cert_to" not in fields and "cert_to" in fn_dates:
            fields["cert_to"] = fn_dates["cert_to"]

    # Step 5: Last resort date extraction — find any date pairs in text
    if "cert_from" not in fields or "cert_to" not in fields:
        all_dates = _find_all_dates(text)
        parsed_dates = []
        for d in all_dates:
            pd = _parse_au_date(d)
            if pd:
                parsed_dates.append(pd)
        # Remove duplicates, sort
        parsed_dates = sorted(set(parsed_dates))
        if len(parsed_dates) >= 2 and "cert_from" not in fields:
            # Heuristic: capacity dates are usually the last pair in the text
            fields.setdefault("cert_from", parsed_dates[-2])
            fields.setdefault("cert_to", parsed_dates[-1])

    return fields


# ---------------------------------------------------------------------------
# Folder scanner — detect new COC files in Active Cases
# ---------------------------------------------------------------------------

def scan_active_cases_for_cocs(active_cases_dir: str) -> list[dict]:
    """
    Scan the Active Cases folder tree for COC PDF files.

    Returns a list of dicts with:
        file_path, filename, folder_name (worker folder), modified_time
    """
    results = []
    if not os.path.isdir(active_cases_dir):
        return results

    for worker_folder in os.listdir(active_cases_dir):
        worker_path = os.path.join(active_cases_dir, worker_folder)
        if not os.path.isdir(worker_path):
            continue

        # Walk through Medical/ and Medical/COC/ subfolders
        for root, dirs, files in os.walk(worker_path):
            for f in files:
                if not f.lower().endswith(".pdf"):
                    continue
                # Match COC-related filenames
                f_lower = f.lower()
                if ("coc" in f_lower or "certificate" in f_lower
                        or "capacity" in f_lower or "fitness" in f_lower):
                    full_path = os.path.join(root, f)
                    results.append({
                        "file_path": full_path,
                        "filename": f,
                        "folder_name": worker_folder,
                        "modified_time": os.path.getmtime(full_path),
                    })

    # Sort by modified time (newest first)
    results.sort(key=lambda x: x["modified_time"], reverse=True)
    return results
