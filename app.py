import hmac
import io
import os

import pandas as pd
import streamlit as st

import ahpra

st.set_page_config(page_title="AHPRA profile extractor", layout="wide")


# --------------------------------------------------------------------------
# Password gate
# --------------------------------------------------------------------------
def get_expected_password():
    try:
        pw = st.secrets.get("APP_PASSWORD")
    except Exception:
        pw = None
    return pw or os.environ.get("APP_PASSWORD")


def check_password():
    if st.session_state.get("authed"):
        return
    expected = get_expected_password()
    if not expected:
        if os.environ.get("ALLOW_NO_PASSWORD") == "1":
            return
        st.error(
            "No password is configured. Add `APP_PASSWORD` to the app's Secrets "
            "(or set the environment variable ALLOW_NO_PASSWORD=1 for testing)."
        )
        st.stop()

    st.title("AHPRA profile extractor")
    with st.form("login"):
        entered = st.text_input("Password", type="password")
        ok = st.form_submit_button("Enter")
    if ok:
        if hmac.compare_digest(entered.encode(), expected.encode()):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


check_password()

st.session_state.setdefault("rows", [])
st.session_state.setdefault("dupes", 0)
st.session_state.setdefault("no_profiles", False)


def to_excel_bytes(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
        ws = writer.sheets["Results"]
        for col in ws.columns:
            width = max(len(str(c.value or "")) for c in col) + 2
            ws.column_dimensions[col[0].column_letter].width = min(width, 45)
    return buf.getvalue()


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
st.title("AHPRA profile extractor")
st.markdown(
    "This tool **does not contact AHPRA**. For each person, search on the "
    "[AHPRA register](https://www.ahpra.gov.au/Registration/Registers-of-Practitioners), "
    "open their profile, press **Ctrl+A** then **Ctrl+C** (Cmd on Mac), and paste into the "
    "box below. Paste as many profiles as you like, one after another."
)

with st.form("extract"):
    pasted = st.text_area(
        "Pasted profile pages", height=300,
        placeholder="Paste the copied text of one or more profile pages here...",
    )
    expected_text = st.text_area(
        "Your list of registration numbers (optional)", height=100,
        placeholder="NMW0002122705\n...",
        help="If you add your list, any number with no pasted profile shows as 'Not found', "
             "and rows follow your order.",
    )
    c1, c2 = st.columns([1, 5])
    go = c1.form_submit_button("Extract details", type="primary")
    clear = c2.form_submit_button("Clear results")

if clear:
    st.session_state.rows = []
    st.session_state.dupes = 0
    st.session_state.no_profiles = False

if go:
    expected = ahpra.parse_numbers(expected_text)
    rows, dupes = ahpra.build_rows(pasted, expected)
    st.session_state.rows = rows
    st.session_state.dupes = dupes
    st.session_state.no_profiles = bool(pasted.strip()) and not ahpra.parse_pasted(pasted)[0]

if st.session_state.no_profiles:
    st.warning(
        "Couldn't find any profile in the pasted text. Make sure you opened a practitioner's "
        "profile page (not the search results) before pressing Ctrl+A and Ctrl+C."
    )

df = pd.DataFrame(st.session_state.rows, columns=ahpra.COLUMNS)
if not df.empty:
    if st.session_state.dupes:
        st.caption(f"{st.session_state.dupes} duplicate profile(s) in the paste were skipped.")
    st.dataframe(df, hide_index=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Found", int((df["Result"] == "Found").sum()))
    m2.metric("Not found", int((df["Result"] == "Not found").sum()))
    m3.metric("Conditions flagged", int((df["Has conditions"] == "Yes").sum()))

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="ahpra_results.csv",
        mime="text/csv",
    )
    d2.download_button(
        "Download Excel",
        to_excel_bytes(df),
        file_name="ahpra_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.caption(
        "'Has conditions' is Yes if any Conditions entry on the profile is not 'None'. "
        "'Check manually' means no Conditions entry could be read."
    )
