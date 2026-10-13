# AHPRA profile extractor

Files: `app.py` (interface), `ahpra.py` (text parsing), `requirements.txt`.

This app does NOT contact AHPRA and needs no browser or system packages. You open each
profile on the public register yourself, press Ctrl+A / Ctrl+C, and paste the text into
the app. It extracts: name (title removed), profession, registration status, date of first
registration, suburb, state, and whether any conditions are listed (Yes / No / Check manually),
with CSV and Excel downloads.

## Deploy on streamlit.app
1. Replace `app.py`, `ahpra.py`, `requirements.txt` and `README.md` in the repo.
2. DELETE `packages.txt` from the repo (no longer needed).
3. Keep the `APP_PASSWORD` secret as it is.

## Using it
- Paste one or more profiles (one after another) and click "Extract details".
- Please check AHPRA's website terms, and ask them for written consent if in doubt.
