"""Render the static 100 × 100 PNG pack icon from a pose of the Hello sticker."""

import argparse
import gzip
from pathlib import Path

from PIL import Image
from rlottie_python import LottieAnimation

from export import framing

SIZE = 100
SOURCE = "01-hello.tgs"
FRAME = 71


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="directory of .tgs files")
    parser.add_argument("output", type=Path, help="path of the PNG to write")
    args = parser.parse_args()
    data = gzip.decompress((args.source / SOURCE).read_bytes()).decode("utf-8")
    with LottieAnimation.from_data(data=data) as animation:
        count = animation.lottie_animation_get_totalframe()
        surface = animation.render_pillow_frame(FRAME).crop(framing(animation, count))
    # rlottie returns premultiplied color channels in its BGRA surface.
    premultiplied = Image.frombytes("RGBa", surface.size, surface.tobytes())
    icon = premultiplied.resize((SIZE, SIZE), Image.Resampling.LANCZOS).convert("RGBA")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    icon.save(args.output, format="PNG", optimize=True)
    print(args.output, args.output.stat().st_size)


if __name__ == "__main__":
    main()
