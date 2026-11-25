"""QT-3 BGM 单元测试：曲库 + 选曲逻辑 + FFmpeg 混音（不依赖数据库）"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TEST_VIDEO = BACKEND / "testdata" / "test_video.mp4"

from app.services import music  # noqa: E402
from app.services._media import has_audio, media_duration  # noqa: E402


def test_list_tracks():
    tracks = music.list_tracks()
    assert len(tracks) >= 5
    assert all({"id", "title", "moods", "duration_s", "license"} <= set(t) for t in tracks)


def test_match_default():
    t = music.match_bgm(60.0)
    assert t["title"] == "Connecting Rainbows"  # 默认曲
    assert t["license"].startswith("CC0")


def test_match_by_track_id():
    t = music.match_bgm(60.0, track_id="energizing")
    assert t["id"] == "energizing"
    assert Path(t["file"]).is_file()


def test_match_unknown_track_raises():
    try:
        music.match_bgm(60.0, track_id="nope")
        raise AssertionError("should raise")
    except ValueError:
        pass


def test_match_by_mood():
    t = music.match_bgm(30.0, mood="calm")
    assert "calm" in t["moods"]
    # 短视频：命中 mood 的曲目里取时长 ≥ 视频的最短曲 → meditating-beat(157s)
    assert t["id"] == "meditating-beat"
    # 超长视频：取最长曲（循环铺满）
    t2 = music.match_bgm(1000.0, mood="calm")
    assert t2["id"] == "river-meditation"


def test_mix_with_video(tmp_path):
    src = media_duration(TEST_VIDEO)
    assert has_audio(TEST_VIDEO), "测试视频应带原声（用于验证闪避路径）"

    out = tmp_path / "mixed.mp4"
    track = music.match_bgm(src, mood="upbeat")
    music.mix_with_video(TEST_VIDEO, track, out)

    assert out.exists() and out.stat().st_size > 0
    assert has_audio(out)
    assert abs(media_duration(out) - src) < 0.5
