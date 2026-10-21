"""Verify the files and hashes recorded for the published release."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        assert path.is_file(), f"Missing release file: {entry['path']}"
        assert path.stat().st_size == entry["bytes"], f"Size mismatch: {entry['path']}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"Hash mismatch: {entry['path']}"
    print(json.dumps({"passed": True, "files_verified": len(manifest["files"]),
                      "training_seeds": manifest["training_seeds"],
                      "paired_bootstrap_seed": manifest["paired_bootstrap_seed"],
                      "scope": "Published file integrity only; no FE validity claim."}))


if __name__ == "__main__":
    main()
