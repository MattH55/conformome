"""Command line: python -m conformome <step> [UniProt accession ...]

Steps mirror the Makefile: download, ingest, map, models, site, validate.
With no accessions, every curation/<accession>.yaml is processed.
"""

from __future__ import annotations

import argparse
import sys

from conformome import pipeline, validate
from conformome.common import default_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conformome")
    parser.add_argument("step", choices=["download", "ingest", "map", "models", "site", "validate"])
    parser.add_argument("accessions", nargs="*")
    args = parser.parse_args(argv)
    paths = default_paths()
    accessions = args.accessions or pipeline.curated_accessions(paths)

    if args.step == "download":
        pipeline.download(paths, accessions)
    elif args.step == "ingest":
        pipeline.ingest(paths, accessions)
    elif args.step == "map":
        for acc in accessions:
            pipeline.map_protein(paths, acc)
    elif args.step == "models":
        for acc in accessions:
            pipeline.models(paths, acc)
    elif args.step == "site":
        from conformome.site.build import build_site
        build_site(paths, accessions)
    elif args.step == "validate":
        errors = validate.run(paths, accessions)
        for err in errors:
            print(f"ERROR {err}", file=sys.stderr)
        print(f"validate: {len(errors)} error(s)")
        return 1 if errors else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
