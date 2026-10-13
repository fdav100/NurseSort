"""AHPRA profile text extractor.

Does NOT contact AHPRA. The user opens each practitioner's profile on the public
register themselves, selects all (Ctrl+A), copies and pastes the text here. This module
pulls the needed fields out of that pasted text.
"""
import re

COLUMNS = [
    "Registration number",
    "Result",
    "Name",
    "Profession",
    "Registration status",
    "Date of first registration",
    "Suburb",
    "State",
    "Has conditions",
    "Notes",
]

TITLES = {
    "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "professor",
    "a/prof", "assoc", "associate", "sir", "dame", "rev",
}

# A line like "No. NMW0002122705" marks the top of each profile
ANCHOR = re.compile(r"^No\.\s*([A-Z]{3}\d{10})$")
DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

# Lines that start a new section (used to know where a "Conditions" block ends)
SECTION_HEADS = {
    "conditions", "undertakings", "reprimands", "registration expiry date",
    "date of first registration in profession", "endorsements", "notations",
    "registration requirements", "personal details", "qualifications",
    "principal place of practice", "registration details", "registration status",
    "registration number", "profession", "what am i looking for?",
}


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def tidy_name(raw):
    tokens = clean(raw).split(" ")
    while len(tokens) > 2 and tokens[0].lower().rstrip(".") in TITLES:
        tokens.pop(0)
    return " ".join(tokens)


def _lines(text):
    return [c for c in (clean(l) for l in (text or "").splitlines()) if c]


def _find(lines, label, start=0, end=None):
    end = len(lines) if end is None else end
    for i in range(start, end):
        if lines[i].lower() == label:
            return i
    return -1


def _value(lines, label, start=0, end=None, not_values=()):
    i = _find(lines, label, start, end)
    if i < 0 or i + 1 >= len(lines):
        return ""
    v = lines[i + 1]
    return "" if v.lower() in not_values else v


def _parse_block(block, number, rel):
    """block = lines for one profile; rel = index of its 'No. XXX' line within the block."""
    notes = []
    row = {c: "" for c in COLUMNS}
    row["Registration number"] = number
    row["Result"] = "Found"

    # Name sits right under the "Registration Details" heading above the "No." line
    heading = -1
    for i in range(rel - 1, -1, -1):
        if block[i].lower() == "registration details":
            heading = i
            break
    name = block[heading + 1] if heading >= 0 and heading + 1 < rel else ""
    row["Name"] = tidy_name(name)
    if not name:
        notes.append("Name not found")

    prof = _value(block, "profession")
    if not prof and heading >= 0 and heading + 2 < rel:
        prof = block[heading + 2]
    row["Profession"] = prof

    row["Registration status"] = _value(block, "registration status")

    # Date of first registration
    date = ""
    i = _find(block, "date of first registration in profession")
    if i >= 0:
        for line in block[i + 1:i + 5]:
            m = DATE.search(line)
            if m:
                date = m.group(0)
                break
    row["Date of first registration"] = date
    if not date:
        notes.append("Date of first registration not found")

    # Conditions: every "Conditions" block on the profile (summary + each division)
    values, found_heading = [], False
    for i, line in enumerate(block):
        if line.lower() != "conditions":
            continue
        found_heading = True
        for nxt in block[i + 1:]:
            low = nxt.lower()
            if low in SECTION_HEADS or low.startswith("division/registration type"):
                break
            if low == "condition":
                continue
            values.append(nxt)
    if not found_heading or not values:
        row["Has conditions"] = "Check manually"
        notes.append("No Conditions entry could be read")
    elif any(v.lower() != "none" for v in values):
        row["Has conditions"] = "Yes"
    else:
        row["Has conditions"] = "No"

    # Principal place of practice (blank if missing)
    suburb = state = ""
    i = _find(block, "principal place of practice")
    if i >= 0:
        end = min(len(block), i + 14)
        stop = {"suburb", "state", "postcode", "country"}
        suburb = _value(block, "suburb", i, end, stop)
        state = _value(block, "state", i, end, stop)
    row["Suburb"], row["State"] = suburb, state

    row["Notes"] = "; ".join(notes)
    return row


def parse_pasted(text):
    """Return (rows in paste order, number of duplicate profiles skipped)."""
    lines = _lines(text)
    anchors = [i for i, l in enumerate(lines) if ANCHOR.match(l)]
    rows, seen, dupes = [], set(), 0
    for k, a in enumerate(anchors):
        prev = anchors[k - 1] + 1 if k else 0
        start = max(a - 8, prev)
        nxt = anchors[k + 1] - 8 if k + 1 < len(anchors) else len(lines)
        end = max(nxt, a + 1)
        block = lines[start:end]
        number = ANCHOR.match(lines[a]).group(1)
        if number in seen:
            dupes += 1
            continue
        seen.add(number)
        rows.append(_parse_block(block, number, a - start))
    return rows, dupes


def not_found_row(number):
    row = {c: "" for c in COLUMNS}
    row["Registration number"] = number
    row["Result"] = "Not found"
    row["Notes"] = ("No profile pasted for this number "
                    "(not found on the register, or not pasted yet)")
    return row


def build_rows(pasted_text, expected=None):
    """Combine pasted profiles with an optional list of the numbers you expected."""
    parsed, dupes = parse_pasted(pasted_text)
    by_num = {r["Registration number"]: r for r in parsed}
    rows, used = [], set()
    for n in expected or []:
        if n in by_num:
            rows.append(by_num[n])
            used.add(n)
        else:
            rows.append(not_found_row(n))
    for r in parsed:
        if r["Registration number"] in used:
            continue
        if expected:
            r["Notes"] = "; ".join(x for x in (r["Notes"], "Not in your list of numbers") if x)
        rows.append(r)
    return rows, dupes


def parse_numbers(text):
    seen, out = set(), []
    for tok in re.split(r"[\s,;]+", (text or "").upper()):
        if tok and tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out
