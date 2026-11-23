"""Render the Ferris animations to transparent VP9 WebM and opaque H.264 MP4."""

import argparse
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageFilter
from rlottie_python import LottieAnimation

from export import framing, sticker_sources


SIZE = 512
MATTE = "0xf1ece3"


def video_frame(animation, frame_number, source_size, crop):
    surface = animation.render_pillow_frame(
        frame_number, width=source_size[0] * 2, height=source_size[1] * 2
    ).crop(crop)
    # Resize in premultiplied color to preserve the coverage at translucent edges.
    premultiplied = Image.frombytes("RGBa", surface.size, surface.tobytes())
    small = premultiplied.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    rgba = small.convert("RGBA")
    # 4:2:0 samples chroma across the boundary. Extend nearby color under zero alpha.
    alpha = rgba.getchannel("A")
    bleed = small.filter(ImageFilter.BoxBlur(2)).convert("RGBA")
    bleed.putalpha(0)
    rgba.paste(bleed, mask=alpha.point([255] + [0] * 255))
    return rgba


def ffmpeg_args(ffmpeg, fps, webm, mp4):
    convert = "scale=out_color_matrix=bt709:out_range=tv"
    graph = (
        f"[0:v]split=2[vp][fg];[vp]{convert},format=yuva420p[alpha];"
        f"color=c={MATTE}:s={SIZE}x{SIZE}:r={fps},format=rgb24[bg];"
        f"[bg][fg]overlay=format=rgb:shortest=1,{convert},format=yuv420p[matte]"
    )
    color = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
             "-color_trc", "iec61966-2-1"]
    return [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "rawvideo",
        "-pix_fmt", "rgba", "-s", f"{SIZE}x{SIZE}", "-framerate", str(fps), "-i", "pipe:0",
        "-filter_complex_threads", "1", "-filter_complex", graph,
        "-map", "[alpha]", "-an", "-c:v", "libvpx-vp9", "-lossless", "1", "-b:v", "0",
        "-auto-alt-ref", "0", "-lag-in-frames", "0", "-row-mt", "1", "-cpu-used", "4", "-threads", "2",
        *color, str(webm),
        "-map", "[matte]", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "12",
        "-threads", "2", "-movflags", "+faststart", *color, str(mp4),
    ]


def render(ffmpeg, raw, output, slug):
    data = gzip.decompress(raw).decode("utf-8")
    doc = json.loads(data)
    count = int(doc["op"] - doc["ip"])
    with tempfile.TemporaryDirectory(dir=output) as stage, LottieAnimation.from_data(data=data) as animation:
        name = "ferris-" + slug
        webm = Path(stage) / (name + ".webm")
        mp4 = Path(stage) / (name + ".mp4")
        crop = tuple(2 * n for n in framing(animation, count))
        size = animation.lottie_animation_get_size()
        command = ffmpeg_args(ffmpeg, doc["fr"], webm, mp4)
        with subprocess.Popen(command, stdin=subprocess.PIPE) as encoder:
            for index in range(count):
                encoder.stdin.write(video_frame(animation, index, size, crop).tobytes())
            encoder.stdin.close()
            if encoder.wait():
                raise subprocess.CalledProcessError(encoder.returncode, command)
        ffprobe = Path(ffmpeg).with_name("ffprobe" + Path(ffmpeg).suffix)
        for asset in (webm, mp4):
            packets = subprocess.check_output([
                str(ffprobe), "-v", "error", "-select_streams", "v:0", "-count_packets",
                "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(asset)
            ], text=True).strip()
            if int(packets) != count:
                raise ValueError(f"{asset.name}: expected {count} video frames, received {packets}")
        for asset in (webm, mp4):
            asset.replace(output / asset.suffix[1:] / asset.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Telegram ZIP or a directory of .tgs files")
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg with libvpx-vp9 and libx264")
    parser.add_argument("--only", metavar="SLUG", action="append", help="export a named sticker, e.g. popcorn")
    args = parser.parse_args()
    selected = set(args.only or ())
    sources = {}
    for stem, raw in sticker_sources(args.source):
        prefix, sep, slug = stem.partition("-")
        sources[slug if sep and prefix.isdigit() else stem] = raw
    if not sources:
        parser.error("No .tgs files found in the input")
    if selected - sources.keys():
        parser.error("Unknown sticker: " + ", ".join(sorted(selected - sources.keys())))
    for profile in ("webm", "mp4"):
        (args.output / profile).mkdir(parents=True, exist_ok=True)
    for slug, raw in sources.items():
        if not selected or slug in selected:
            render(args.ffmpeg, raw, args.output, slug)
            print(slug, flush=True)


if __name__ == "__main__":
    main()
