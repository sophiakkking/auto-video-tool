"""字幕引擎（QT-1/4/6）— sherpa-onnx ASR + ffmpeg drawtext 烧录

本机说明：faster-whisper 的 ctranslate2 在此机器上崩溃（segfault，4.6/4.9 均复现），
ASR 引擎采用 sherpa-onnx（pip 包自带 onnxruntime 预编译，稳定可靠）。
模型文件位于 ~/tools/sherpa-onnx/models/（encoder/decoder int8 onnx + tokens）。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ._media import ffmpeg

_recognizers: dict = {}


def _model_dir() -> Path:
    return Path.home() / "tools" / "sherpa-onnx" / "models"


def _get_recognizer(model_size: str, language: str | None):
    key = (model_size, language)
    if key in _recognizers:
        return _recognizers[key]

    import sherpa_onnx

    d = _model_dir()
    enc = d / f"{model_size}-encoder.int8.onnx"
    dec = d / f"{model_size}-decoder.int8.onnx"
    tok = d / f"{model_size}-tokens.txt"
    missing = [f.name for f in (enc, dec, tok) if not f.exists()]
    if missing:
        raise RuntimeError(
            f"缺少 ASR 模型文件: {missing}（见 ~/tools/sherpa-onnx/models/，"
            f"下载地址: huggingface.co/csukuangfj/sherpa-onnx-whisper-{model_size}）"
        )

    recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(enc),
        decoder=str(dec),
        tokens=str(tok),
        num_threads=4,
        language=language or "",  # 空串 = 自动检测
        task="transcribe",
        tail_paddings=-1,
        # 不传 enable_token_timestamps：本机模型无注意力输出，
        # 开启只会刷警告，时间轴改由静音分段保证（见 transcribe）
    )
    _recognizers[key] = recognizer
    return recognizer


def _load_audio_np(media_path: str | Path):
    """用 ffmpeg 解码为 16kHz 单声道 float32"""
    import numpy as np

    cmd = [
        ffmpeg(), "-v", "error", "-i", str(media_path),
        "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1",
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 解码失败: {r.stderr.decode(errors='ignore')[:300]}")
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def _tok(t) -> str:
    if isinstance(t, bytes):
        return t.decode("utf-8", errors="replace")
    return str(t)


def _silence_boundaries(
    media_path: str | Path, noise_db: int = -35, min_silence: float = 0.5
) -> list[tuple[float, float]]:
    """ffmpeg silencedetect 找静音区间 → [(start, end), ...]"""
    import re

    r = subprocess.run(
        [
            ffmpeg(), "-i", str(media_path),
            "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def _speech_chunks(
    silences: list[tuple[float, float]],
    total_s: float,
    max_chunk: float = 20.0,
    min_speech: float = 0.6,
) -> list[tuple[float, float]]:
    """静音区间之间的有声段；过短合并，过长切分"""
    chunks: list[tuple[float, float]] = []
    cursor = 0.0
    for s_start, s_end in silences:
        if s_start - cursor >= min_speech:
            chunks.append((cursor, s_start))
        cursor = s_end
    if total_s - cursor >= min_speech:
        chunks.append((cursor, total_s))
    # 过长的块按 1/2 递归切分
    out: list[tuple[float, float]] = []
    for a, b in chunks:
        if b - a > max_chunk:
            mid = a + (b - a) / 2
            out.append((a, mid))
            out.append((mid, b))
        else:
            out.append((a, b))
    return out


_opencc = None


def _normalize_zh(text: str) -> str:
    """繁体→简体（whisper 偶尔输出繁体字）；纯非中文文本原样返回"""
    global _opencc
    if not any("一" <= ch <= "鿿" for ch in text):
        return text
    if _opencc is None:
        try:
            from opencc import OpenCC

            _opencc = OpenCC("t2s")
        except ImportError:  # 未安装时优雅降级
            _opencc = False
    return _opencc.convert(text) if _opencc else text


def transcribe(
    media_path: str | Path,
    language: str | None = None,
    model_size: str = "small",
) -> list[dict]:
    """ASR 转写 → [{start, end, text}]（秒）

    流程：ffmpeg 静音检测分段 → 逐段 sherpa-onnx 转写 → 段时间轴天然对齐。
    不依赖逐词时间戳（本机模型无注意力输出，且 sherpa 2.x tokens 属性有解码 bug）。
    """
    recognizer = _get_recognizer(model_size, language)
    audio = _load_audio_np(media_path)
    total_s = len(audio) / 16000
    silences = _silence_boundaries(media_path)
    chunks = _speech_chunks(silences, total_s) or [(0.0, total_s)]

    segs: list[dict] = []
    for start_s, end_s in chunks:
        chunk = audio[int(start_s * 16000): int(end_s * 16000)]
        if len(chunk) < 1600:  # < 0.1s 跳过
            continue
        stream = recognizer.create_stream()
        stream.accept_waveform(16000, chunk)
        recognizer.decode_stream(stream)
        text = _normalize_zh((stream.result.text or "").strip())
        if text:
            segs.append({"start": round(start_s, 2), "end": round(end_s, 2), "text": text})
    return segs


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt(segments: list[dict]) -> str:
    """导出标准 SRT（QT-1 可选导出）"""
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(
            f"{i}\n{_fmt_ts(seg['start'])} --> {_fmt_ts(seg['end'])}\n{seg['text']}\n"
        )
    return "\n".join(lines)


def export_ass(
    segments: list[dict],
    width: int = 720,
    height: int = 1280,
    font_name: str = "Microsoft YaHei",
    font_size: int | None = None,
    caption_style: str = "big",
) -> str:
    """生成 ASS 字幕文件（libass 烧录用，带半透明底框）"""
    if font_size is None:
        font_size = max(28, int(height * 0.06))
    # BorderStyle=3 底框；BackColour 半透明黑
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H78000000,0,0,0,0,100,100,0,0,3,2,0,2,10,10,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for seg in segments:
        start = _ass_ts(seg["start"])
        end = _ass_ts(seg["end"])
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{seg['text']}")
    return "\n".join(lines) + "\n"


def _ass_ts(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def burn_subtitles(
    video_path: str | Path,
    segments: list[dict],
    out_path: str | Path,
    font_file: str | None = None,
    font_size: int | None = None,
    caption_style: str = "big",
) -> str:
    """把字幕烧录进视频：ASS → libass 单滤镜（subtitle filter），返回输出路径"""
    from ._media import video_size

    # cwd 会被切到 ass 临时目录，入参先转绝对路径，避免相对路径失效
    video_path = Path(video_path).resolve()
    out_path = Path(out_path).resolve()
    if not segments:
        shutil.copyfile(str(video_path), str(out_path))
        return str(out_path)

    width, height = video_size(video_path)
    ass = export_ass(segments, width=width, height=height, font_size=font_size)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".ass", delete=False, encoding="utf-8"
    ) as f:
        f.write(ass)
        ass_path = f.name

    # 工作目录切到 ass 所在目录，用相对文件名避免冒号转义问题
    tmp_dir = Path(ass_path).parent
    fontsdir = "C\\:/Windows/Fonts"
    vf = f"subtitles={Path(ass_path).name}:fontsdir='{fontsdir}'"
    try:
        cmd = [
            ffmpeg(), "-y", "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac",
            str(out_path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_dir))
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg 失败: {r.stderr[-400:]}")
    finally:
        Path(ass_path).unlink(missing_ok=True)
    return str(out_path)
