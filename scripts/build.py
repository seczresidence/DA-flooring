"""Build the DA Flooring page from the Google Sheet "Flooring" (tab DA_Flooring).

Usage:
  GCP_SA_KEY='<service account JSON>' python scripts/build.py          # fetch from Google
  python scripts/build.py --local data.json                            # use a saved copy (testing)

Writes site/index.html. Exits with an error, and builds nothing, when the sheet
cannot be read or its header is not as expected, so the live page stays as it was.
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.parse
import zoneinfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHEET_ID = os.environ.get("SHEET_ID", "1xPIF0L-8NAwdra_KCYxxm6ftXvdCJlCWu11rvCPAQ9c")
TAB = os.environ.get("SHEET_TAB", "DA_Flooring")
COLUMNS = ["Week", "Store", "REF", "WM", "SKU", "Brand/Multibrand", "Orig price",
           "Action price", "Incentive before action", "Comments", "GSCM"]


def fetch_values():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    info = json.loads(os.environ["GCP_SA_KEY"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                      "https://www.googleapis.com/auth/drive.readonly"])
    session = AuthorizedSession(creds)
    rng = urllib.parse.quote(f"{TAB}!A1:Z")
    r = session.get(f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{rng}",
                    params={"valueRenderOption": "FORMATTED_VALUE"}, timeout=60)
    if r.ok:
        return r.json().get("values", [])
    print(f"Sheets API failed ({r.status_code}): {r.text[:300]}", file=sys.stderr)
    print("Falling back to Drive CSV export of the first tab.", file=sys.stderr)
    import csv, io
    r2 = session.get(f"https://www.googleapis.com/drive/v3/files/{SHEET_ID}/export",
                     params={"mimeType": "text/csv"}, timeout=60)
    r2.raise_for_status()
    return list(csv.reader(io.StringIO(r2.content.decode("utf-8"))))


def encrypt(text, password):
    """AES-256-GCM with a key from PBKDF2-SHA256; the page decrypts it in the browser."""
    import base64, secrets
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt, iv, iterations = secrets.token_bytes(16), secrets.token_bytes(12), 250_000
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(password.encode())
    ct = AESGCM(key).encrypt(iv, text.encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    return json.dumps({"enc": 1, "iter": iterations, "salt": b(salt), "iv": b(iv), "ct": b(ct)})


def normalise(values):
    if not values:
        sys.exit("The sheet is empty.")
    header = [h.strip() for h in values[0]]
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        sys.exit(f"Sheet header changed, missing columns: {missing}. Found: {header}")
    idx = [header.index(c) for c in COLUMNS]
    rows = []
    for raw in values[1:]:
        raw = list(raw) + [""] * (len(header) - len(raw))
        row = [" ".join(str(raw[i]).split()) for i in idx]  # tabs/newlines -> single spaces
        if any(row):
            rows.append(row)
    if len(rows) < 10:
        sys.exit(f"Only {len(rows)} rows read; refusing to publish a near-empty page.")
    return rows


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        values = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
        values = values.get("values", values) if isinstance(values, dict) else values
    else:
        values = fetch_values()
    rows = normalise(values)
    now = datetime.datetime.now(zoneinfo.ZoneInfo("Europe/Prague"))
    password = os.environ.get("PAGE_PASSWORD", "")
    doc = {"updated": now.strftime("%-d. %-m. %Y %H:%M"), "rows": rows}
    token = os.environ.get("DISPATCH_TOKEN", "")
    if token and password:  # the refresh token is only ever published inside the encrypted data
        doc["refresh"] = {"repo": os.environ.get("GITHUB_REPOSITORY", "seczresidence/DA-flooring"),
                          "workflow": "update.yml", "token": token}
    data = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if password:
        data = encrypt(data, password)
    elif os.environ.get("GITHUB_ACTIONS"):
        sys.exit("Secret PAGE_PASSWORD is not set; refusing to publish the data without a password.")
    payload = data.replace("</", "<\\/")
    html = (ROOT / "template.html").read_text(encoding="utf-8")
    assert "__DATA__" in html
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(html.replace("__DATA__", payload), encoding="utf-8")
    import shutil
    shutil.copytree(ROOT / "assets", out / "assets", dirs_exist_ok=True)
    weeks = sorted({r[0] for r in rows if r[0]})
    print(f"Built site/index.html: {len(rows)} rows, weeks {', '.join(weeks)}, {now:%Y-%m-%d %H:%M} Prague")


if __name__ == "__main__":
    main()
