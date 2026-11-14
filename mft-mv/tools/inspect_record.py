from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work" / "audio-libs"))

import av
from PIL import Image, ImageDraw, ImageFont

SOURCE = ROOT / "asset" / "record" / "record.mp4"
OUT = ROOT / "work" / "record-overview"
OUT.mkdir(parents=True, exist_ok=True)
FRAME_COUNT = 30
COLS, ROWS = 5, 3
THUMB_W, THUMB_H = 320, 180
LABEL_H = 28
PER_PAGE = COLS * ROWS


def frame_at(container, stream, seconds):
    container.seek(int(seconds / stream.time_base), stream=stream, backward=True)
    for frame in container.decode(stream):
        if frame.time is not None and frame.time >= seconds - 0.06:
            return frame.to_image()
    raise RuntimeError(f"No decoded frame at {seconds:.3f}s")


container = av.open(str(SOURCE))
stream = container.streams.video[0]
duration = float(stream.duration * stream.time_base)
times = [duration * i / FRAME_COUNT for i in range(FRAME_COUNT)]
font = ImageFont.load_default(size=18)
metadata = []

for page_start in range(0, FRAME_COUNT, PER_PAGE):
    page_times = times[page_start:page_start + PER_PAGE]
    page_rows = (len(page_times) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * THUMB_W, page_rows * (THUMB_H + LABEL_H)), "#15121d")
    draw = ImageDraw.Draw(sheet)
    for local_index, seconds in enumerate(page_times):
        index = page_start + local_index
        image = frame_at(container, stream, seconds)
        image.thumbnail((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
        x = (local_index % COLS) * THUMB_W
        y = (local_index // COLS) * (THUMB_H + LABEL_H)
        sheet.paste(image, (x + (THUMB_W - image.width) // 2, y))
        draw.text((x + 8, y + THUMB_H + 3), f"#{index:02d}  {seconds:07.3f}s", fill="white", font=font)
        metadata.append({"index": index, "seconds": seconds})
    path = OUT / f"page-{page_start // PER_PAGE + 1}.jpg"
    sheet.save(path, quality=88, optimize=True)
    print(path)

container.close()
(OUT / "times.json").write_text(json.dumps({"duration": duration, "frames": metadata}, indent=2), encoding="utf-8")
print(f"duration={duration:.6f}s")
