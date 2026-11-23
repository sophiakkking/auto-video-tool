"""封面生成（QT-2/IM-4）— 最佳帧 + 平台规格裁剪 + 大字标题"""
from __future__ import annotations

import subprocess
from pathlib import Path

from ._media import ffmpeg

DEFAULT_FONT = "C:/Windows/Fonts/msyh.ttc"

# 平台封面规格（与风格档案保持一致，Phase 2 起从 style_profiles 读取）
PLATFORM_SPECS = {
    "xiaohongshu": {"ratio_w": 3, "ratio_h": 4, "title_size_pct": 0.12, "title_position": "top"},
    "instagram": {"ratio_w": 1, "ratio_h": 1, "title_size_pct": 0.09, "title_position": "bottom"},
}


def extract_best_frame(video_path: str | Path, out_path: str | Path) -> str:
    """thumbnail 滤镜选取最有代表性的一帧"""
    subprocess.run(
        [
            ffmpeg(), "-y", "-i", str(video_path),
            "-vf", "thumbnail",
            "-frames:v", "1",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return str(out_path)


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > max_w:
            if cur:
                lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines or [text]


def make_cover(
    frame_path: str | Path,
    title: str,
    out_path: str | Path,
    platform: str = "xiaohongshu",
    font_file: str | None = None,
) -> str:
    """居中裁剪到平台比例 + 半透明白带 + 大字标题（自动换行居中）"""
    from PIL import Image, ImageDraw, ImageFont

    font_file = font_file or DEFAULT_FONT
    spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["xiaohongshu"])
    ratio = spec["ratio_w"] / spec["ratio_h"]

    img = Image.open(frame_path).convert("RGB")
    w, h = img.size
    if w / h > ratio:  # 太宽 → 裁宽
        new_w = int(h * ratio)
        x0 = (w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, h))
    else:  # 太高 → 裁高
        new_h = int(w / ratio)
        y0 = (h - new_h) // 2
        img = img.crop((0, y0, w, y0 + new_h))
    w, h = img.size

    font_size = int(w * spec["title_size_pct"])
    font = ImageFont.truetype(font_file, font_size)

    line_h = int(font_size * 1.3)
    draw = ImageDraw.Draw(img)
    lines = _wrap(draw, title, font, int(w * 0.92))
    band_h = line_h * len(lines) + int(h * 0.04)
    band_y0 = 0 if spec["title_position"] == "top" else h - band_h

    overlay = Image.new("RGBA", (w, band_h), (255, 255, 255, 215))
    img.paste(overlay, (0, band_y0), overlay)

    draw = ImageDraw.Draw(img)
    total_h = len(lines) * line_h
    start_y = band_y0 + (band_h - total_h) // 2 - int(font_size * 0.12)
    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=font)
        draw.text(
            ((w - lw) / 2, start_y + i * line_h),
            line,
            font=font,
            fill=(34, 34, 34),
        )

    img.save(out_path, quality=92)
    return str(out_path)
