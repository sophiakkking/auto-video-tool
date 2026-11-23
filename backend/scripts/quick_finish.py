"""口播一键成片 CLI（QT-4）— Spike 1，纯管线、无需数据库

用法:
    .venv/Scripts/python scripts/quick_finish.py 口播视频.mp4 \
        --title "冬天第一杯热饮" --platform xiaohongshu --out-dir out

流程: ASR 转写 → 字幕烧录 → 封面生成 → 导出
输出: transcript.json / subtitles.srt / finished.mp4 / cover.png
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import cover, subtitles  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="口播一键成片 (QT-4)")
    ap.add_argument("input", help="口播视频文件")
    ap.add_argument("--title", default="", help="封面标题（小红书 ≤20 字）")
    ap.add_argument(
        "--platform", default="xiaohongshu", choices=["xiaohongshu", "instagram"]
    )
    ap.add_argument("--language", default=None, help="转写语言（默认自动检测）")
    ap.add_argument("--model-size", default="small", help="whisper 模型大小")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"[1/4] ASR 转写（model={args.model_size}）…")
    segs = subtitles.transcribe(
        args.input, language=args.language, model_size=args.model_size
    )
    dur = segs[-1]["end"] if segs else 0
    print(f"      {len(segs)} 段字幕 / 语音 {dur:.0f}s")
    (out / "transcript.json").write_text(
        json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "subtitles.srt").write_text(subtitles.export_srt(segs), encoding="utf-8")

    print("[2/4] 字幕烧录…")
    finished = out / "finished.mp4"
    subtitles.burn_subtitles(args.input, segs, finished, caption_style="big")
    print(f"      {finished.name}")

    print("[3/4] 封面生成…")
    frame = out / "_best_frame.png"
    cover.extract_best_frame(args.input, frame)
    cov = out / "cover.png"
    cover.make_cover(frame, args.title, cov, platform=args.platform)
    frame.unlink()
    print(f"      {cov.name}")

    print("[4/4] BGM: QT-3 待接入免版税曲库，本次跳过")
    print(f"\n完成，耗时 {time.time() - t0:.1f}s")
    print(f"输出目录: {out.resolve()}")
    print("导出: transcript.json / subtitles.srt / finished.mp4 / cover.png")


if __name__ == "__main__":
    main()
