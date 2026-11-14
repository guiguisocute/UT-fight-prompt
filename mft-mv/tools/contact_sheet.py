from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work" / "audio-libs"))

import av
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description="Decode evenly spaced video frames into timestamped contact sheets.")
parser.add_argument("source", type=Path)
parser.add_argument("out", type=Path)
parser.add_argument("--start", type=float, default=0.0)
parser.add_argument("--end", type=float)
parser.add_argument("--count", type=int, default=30)
parser.add_argument("--cols", type=int, default=5)
parser.add_argument("--rows", type=int, default=3)
parser.add_argument("--width", type=int, default=320)
args = parser.parse_args()

source = args.source if args.source.is_absolute() else ROOT / args.source
out = args.out if args.out.is_absolute() else ROOT / args.out
out.mkdir(parents=True, exist_ok=True)
container = av.open(str(source))
stream = container.streams.video[0]
duration = float(stream.duration * stream.time_base)
end = min(args.end if args.end is not None else duration, duration)
times = [args.start + (end - args.start) * i / args.count for i in range(args.count)]
thumb_w = args.width
thumb_h = round(thumb_w * stream.height / stream.width)
label_h = 28
per_page = args.cols * args.rows
font = ImageFont.load_default(size=18)
metadata = []


def frame_at(seconds):
    container.seek(int(seconds / stream.time_base), stream=stream, backward=True)
    for frame in container.decode(stream):
        if frame.time is not None and frame.time >= seconds - 0.06:
            return frame.to_image()
    raise RuntimeError(f"No decoded frame at {seconds:.3f}s")


for page_start in range(0, len(times), per_page):
    page_times = times[page_start:page_start + per_page]
    page_rows = (len(page_times) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (args.cols * thumb_w, page_rows * (thumb_h + label_h)), "#15121d")
    draw = ImageDraw.Draw(sheet)
    for local_index, seconds in enumerate(page_times):
        index = page_start + local_index
        image = frame_at(seconds)
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = (local_index % args.cols) * thumb_w
        y = (local_index // args.cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 3), f"#{index:03d}  {seconds:07.3f}s", fill="white", font=font)
        metadata.append({"index": index, "seconds": seconds})
    path = out / f"page-{page_start // per_page + 1}.jpg"
    sheet.save(path, quality=88, optimize=True)
    print(path)

container.close()
(out / "times.json").write_text(json.dumps({"source": str(source), "duration": duration, "frames": metadata}, indent=2), encoding="utf-8")
print(f"duration={duration:.6f}s")
