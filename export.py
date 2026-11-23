"""Export transparent looping GIFs from a Telegram sticker ZIP or a directory of .tgs files.

Install Pillow and rlottie-python, then run:
    python export.py animated-ferris.zip output
    python export.py tgs/ output

emoji/ contains 128 px, 15 fps GIFs for Slack custom emoji.
messages/ contains 384 px, 25 fps GIFs for sharing as message attachments.
"""

import argparse
import gzip
import json
import math
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageChops
from rlottie_python import LottieAnimation

PROFILES = {"emoji": (128, 15), "messages": (384, 25)}


def framing(animation, count):
    left, top = animation.lottie_animation_get_size()
    right = bottom = 0
    for frame in range(count):
        bounds = animation.render_pillow_frame(frame).getbbox()
        if bounds:
            left, top = min(left, bounds[0]), min(top, bounds[1])
            right, bottom = max(right, bounds[2]), max(bottom, bounds[3])
    if right <= left or bottom <= top:
        raise ValueError("The animation is empty.")
    side = math.ceil(max(right - left, bottom - top) / 0.94)
    x, y = (left + right - side) // 2, (top + bottom - side) // 2
    return x, y, x + side, y + side


def sample_loop(animation, frame_count, source_rate, box, size, fps):
    seconds = frame_count / source_rate
    count = max(1, round(seconds * fps))
    times = [round(i * seconds * 100 / count) * 10 for i in range(count + 1)]
    frames = []
    for i in range(count):
        sample = min(frame_count - 1, round(i * frame_count / count))
        surface = animation.render_pillow_frame(sample).crop(box)
        # rlottie returns premultiplied color channels in its BGRA surface.
        premultiplied = Image.frombytes("RGBa", surface.size, surface.tobytes())
        frames.append(premultiplied.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA"))
    return frames, [b - a for a, b in zip(times, times[1:])]


def index_frames(images):
    # A single palette for the loop keeps colors stable as the pose changes.
    atlas = Image.new("RGB", (96, 96 * len(images)))
    for i, im in enumerate(images):
        atlas.paste(im.resize((96, 96), Image.Resampling.BOX).convert("RGB"), (0, i * 96))
    palette = atlas.quantize(colors=127, dither=Image.Dither.NONE)
    swatches = bytes(palette.getpalette())
    transparent = len(swatches) // 3
    colors = swatches + bytes((255, 0, 255))
    indexed = []
    for im in images:
        frame = im.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
        frame.putpalette(colors)
        frame.paste(transparent, mask=im.getchannel("A").point(lambda a: 255 if a < 116 else 0))
        frame.info["transparency"] = transparent
        indexed.append(frame)
    return indexed, colors, transparent


def write_loop(path, frames, palette, transparent, durations):
    frames[0].save(path, format="GIF", save_all=True, append_images=frames[1:],
                   loop=0, duration=durations, transparency=transparent,
                   background=transparent, disposal=2, optimize=False, palette=palette)


def verify(path, frames, durations, custom_emoji):
    with Image.open(path) as gif:
        if gif.info.get("loop") != 0 or gif.size != frames[0].size:
            raise ValueError(f"{path.name}: incorrect loop settings or dimensions")
        if custom_emoji and (gif.n_frames > 50 or path.stat().st_size >= 128_000):
            raise ValueError(f"{path.name}: exceeds Slack custom emoji limits")
        # A GIF writer may coalesce identical poses. Compare at presentation times.
        pos = 0
        for i in range(gif.n_frames):
            gif.seek(i)
            decoded = gif.convert("RGBA").convert("RGBa")
            delay = gif.info["duration"]
            while delay > 0 and pos < len(frames):
                expected = frames[pos].convert("RGBA").convert("RGBa")
                if ImageChops.difference(expected, decoded).getbbox(alpha_only=False):
                    raise ValueError(f"{path.name}: incorrect pixels at sample {pos}")
                delay -= durations[pos]
                pos += 1
            if delay:
                raise ValueError(f"{path.name}: incorrect frame duration")
        if pos != len(frames):
            raise ValueError(f"{path.name}: truncated loop")


def sticker_sources(path):
    if path.is_dir():
        for file in sorted(path.glob("*.tgs")):
            yield file.stem, file.read_bytes()
    else:
        with ZipFile(path) as pack:
            for name in sorted(pack.namelist()):
                if name.endswith(".tgs"):
                    yield Path(name).stem, pack.read(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Telegram sticker ZIP or directory of .tgs files")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    for profile in PROFILES:
        (args.output / profile).mkdir(parents=True, exist_ok=True)
    sources = list(sticker_sources(args.source))
    if not sources:
        parser.error("the input contains no .tgs files")
    for slug, raw in sources:
        prefix, sep, suffix = slug.partition("-")
        if sep and prefix.isdigit():
            slug = suffix
        source = gzip.decompress(raw).decode("utf-8")
        doc = json.loads(source)
        count = round(doc["op"] - doc["ip"])
        with LottieAnimation.from_data(data=source) as animation:
            box = framing(animation, count)
            for profile, (size, fps) in PROFILES.items():
                images, delays = sample_loop(animation, count, doc["fr"], box, size, fps)
                frames, colors, index = index_frames(images)
                out = args.output / profile / f"ferris-{slug}.gif"
                write_loop(out, frames, colors, index, delays)
                verify(out, frames, delays, profile == "emoji")
                print(out, out.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
