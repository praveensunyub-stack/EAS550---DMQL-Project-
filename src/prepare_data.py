"""The three selected CSV files will be extracted from the Synthea ZIP file."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from .validation import SPECS, sha256_file


def prepare(archive, out_dir, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if sha256_file(archive) != manifest["archive"]["sha256"]:
        raise ValueError("ZIP checksum mismatch: obtain the exact supplied snapshot, not a new 'latest' download")
    payloads = {}
    with zipfile.ZipFile(archive) as source:
        for name in SPECS:
            filename = name + ".csv"
            if source.namelist().count(filename) != 1:
                raise ValueError(f"Expected exactly one top-level {filename}")
            payload = source.read(filename)
            if hashlib.sha256(payload).hexdigest() != manifest["files"][filename]["sha256"]:
                raise ValueError(f"CSV checksum mismatch: {filename}")
            payloads[filename] = payload
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    # No extractall: only literal filenames in SPECS can be written.
    for filename, payload in payloads.items():
        (destination / filename).write_bytes(payload)
    return {name: manifest["files"][name]["rows"] for name in payloads}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--zip", dest="archive", type=Path, help="Use the original user-supplied archive")
    source.add_argument("--bundled", action="store_true", help="Use the committed selected-column snapshot")
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path,
                        help="Override manifest; defaults to subset_manifest.json for --bundled, manifest.json for --zip")
    args = parser.parse_args()
    archive = Path("data/phase1_subset.zip") if args.bundled else args.archive
    manifest = args.manifest or Path("data/subset_manifest.json" if args.bundled else "data/manifest.json")
    try:
        counts = prepare(archive, args.out, manifest)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Input preparation failed: {exc}\n")
    print(json.dumps({"status": "prepared", "expected_rows": counts, "output": str(args.out)}))


if __name__ == "__main__":
    main()
