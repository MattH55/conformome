#!/usr/bin/env python3
"""Create the Conformome data deposit on Zenodo via its REST API.

Creates a draft, uploads the files and sets the metadata. It does NOT publish unless you pass
--publish. Check the draft in the browser first; publishing is permanent, and a published DOI
cannot be deleted.

    export ZENODO_TOKEN=...          # zenodo.org > Account > Applications > Personal access token
                                     # scopes: deposit:write and deposit:actions
    python3 zenodo_upload_data.py --sandbox  release/        # trial run on sandbox.zenodo.org
    python3 zenodo_upload_data.py release/                   # real draft on zenodo.org
    python3 zenodo_upload_data.py release/ --publish         # draft + publish in one go

A sandbox token is separate: make it at https://sandbox.zenodo.org with its own account.
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def call(method, url, token, data=None, raw=None, ctype="application/json"):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=600) as r:
        txt = r.read()
    return json.loads(txt) if txt else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="folder holding exactly the files to deposit")
    ap.add_argument("--metadata", type=Path, default=HERE / "zenodo_data_metadata.json")
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()

    token = os.environ.get("ZENODO_TOKEN") or sys.exit("set ZENODO_TOKEN")
    base = "https://sandbox.zenodo.org/api" if a.sandbox else "https://zenodo.org/api"
    meta = json.loads(a.metadata.read_text(encoding="utf-8"))
    if "SOFTWARE_VERSION_DOI" in json.dumps(meta):
        sys.exit("fill in the software version DOI in the metadata file first")
    if "0000-0000-0000-0000" in json.dumps(meta):
        sys.exit("fill in your ORCID in the metadata file first")

    files = sorted(p for p in a.folder.iterdir() if p.is_file())
    if not files:
        sys.exit(f"no files in {a.folder}")
    print("files:", *[f"  {p.name} ({p.stat().st_size/1e6:.1f} MB)" for p in files], sep="\n")

    dep = call("POST", f"{base}/deposit/depositions", token, data={})
    bucket = dep["links"]["bucket"]
    for p in files:
        with p.open("rb") as fh:
            call("PUT", f"{bucket}/{p.name}", token, raw=fh.read(), ctype="application/octet-stream")
        print("uploaded", p.name)
    call("PUT", f"{base}/deposit/depositions/{dep['id']}", token, data=meta)
    print("draft:", dep["links"]["html"])
    print("reserved DOI:", dep.get("metadata", {}).get("prereserve_doi", {}).get("doi", "(see draft page)"))
    if a.publish:
        out = call("POST", f"{base}/deposit/depositions/{dep['id']}/actions/publish", token)
        print("published:", out.get("doi"), out["links"]["html"])
    else:
        print("not published: review the draft in the browser, then click Publish")


if __name__ == "__main__":
    main()
