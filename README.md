# Animated Ferris

Animated Ferris is a pack of twenty wordless animated Telegram stickers featuring Ferris the crab. This repository contains the vector sources and the scripts that build the Telegram stickers, Slack GIFs, videos and the pack icon.

| | Sticker | Emoji |
|---|---|---|
| 01 | Hello | 👋 |
| 02 | Love | ❤️ |
| 03 | Hooray | 🎉 |
| 04 | Side-eye | 👀 |
| 05 | Phew | 😅 |
| 06 | Sleepy | 😴 |
| 07 | Ship it | 📦 |
| 08 | Joy | 😂 |
| 09 | Investigating | 🔎 |
| 10 | Freezing | 🥶 |
| 11 | Gotta go | 🏃 |
| 12 | Popcorn | 🍿 |
| 13 | Thank you | 🙏 |
| 14 | Heart eyes | 😍 |
| 15 | Dizzy | 😵‍💫 |
| 16 | Cool | 😎 |
| 17 | Ugly cry | 😭 |
| 18 | Mind blown | 🤯 |
| 19 | Party horn | 🥳 |
| 20 | Shrug | 🤷 |

## Sources

Each numbered JSON document in `animations/` contains the complete vector drawing, keyframes, easing and timing of one sticker. Open it in [Glaxnimate](https://docs.glaxnimate.org/en/formats.html) or a text editor. The `fr` field is the frame rate, `ip` is the first frame and `op` is the exclusive end frame. At 60 fps, 168 frames make a 2.8-second loop and 180 frames make a 3-second loop. Use only the shape and animation features that [Telegram supports](https://core.telegram.org/stickers#animated-stickers-and-emoji).

The SVGs in `artwork/` are the starting poses, based on Karen Rustad Tölva's Flat, Happy and Gesturing Ferris drawings, which are dedicated to the public domain. [Ferris artwork gallery](https://rustacean.net/)

## Build

The scripts run with [uv](https://docs.astral.sh/uv/) and write everything to `dist/`.

```sh
uv run build_tgs.py
uv run export.py dist/tgs dist/gifs
uv run export_videos.py dist/tgs dist/videos
uv run export_icon.py dist/tgs dist/pack-icon.png
```

`build_tgs.py` compacts each JSON document and compresses it with gzip into a `.tgs` sticker. Run `gzip -dc dist/tgs/12-popcorn.tgs | python3 -m json.tool` to inspect one.

`export.py` renders two sets of transparent GIFs. Use the larger `messages/` files for Slack attachments and the smaller `emoji/` files for Slack custom emoji.

`export_videos.py` needs FFmpeg and ffprobe with the libvpx-vp9 and libx264 encoders. It writes transparent VP9 video to `webm/` and H.264 video on a warm off-white background to `mp4/`. Use `--only popcorn` to render a single sticker.

`export_icon.py` renders a static waving Ferris as a 100 × 100 PNG for the pack icon.

## Publish on Telegram

Open [@Stickers](https://t.me/Stickers), send `/newanimated` and upload each numbered `.tgs` file from `dist/tgs/` with its emoji from the table above. Send `/publish` when the set is complete.

## License

Like the original Ferris artwork, this project is dedicated to the public domain under [CC0 1.0](LICENSE).
