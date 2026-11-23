"""Rebuild the Telegram stickers from the adjacent Lottie JSON sources."""

import argparse
import gzip
import json
from pathlib import Path


def build(source):
    animation = json.loads(source.read_text(encoding="utf-8"))
    frames = animation["op"] - animation["ip"]
    if (animation["w"], animation["h"], animation["fr"]) != (512, 512, 60):
        raise ValueError(f"{source.name} needs a 512 × 512 canvas and 60 fps")
    if not 0 < frames <= 180 or animation.get("tgs") != 1:
        raise ValueError(f"{source.name} needs a Telegram animation of up to three seconds")
    payload = json.dumps(animation, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    compressed = gzip.compress(payload.encode("utf-8"), compresslevel=9, mtime=0)
    if len(compressed) > 65536:
        raise ValueError(f"{source.name} exceeds Telegram's 64 KB limit")
    return compressed


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "dist" / "tgs", help="output directory (default: dist/tgs/ next to this script)")
    args = parser.parse_args()
    files = sorted((root / "animations").glob("*.json"))
    if not files:
        parser.error("No JSON files found in animations/ next to this script")
    try:
        stickers = {source.stem: build(source) for source in files}
    except (OSError, KeyError, ValueError, TypeError) as exc:
        parser.exit(1, f"{exc}\n")
    args.output.mkdir(parents=True, exist_ok=True)
    for stem, data in stickers.items():
        (args.output / (stem + ".tgs")).write_bytes(data)
    print(f"Wrote {len(stickers)} stickers to {args.output}")


if __name__ == "__main__":
    main()
