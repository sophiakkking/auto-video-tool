from fastapi.testclient import TestClient

from app.main import app


def test_styles_returns_seed_profiles():
    """数据库未就绪时也应返回种子风格档案（技术设计 §8）"""
    with TestClient(app) as client:
        r = client.get("/v1/styles")
        assert r.status_code == 200
        platforms = {p["platform"] for p in r.json()}
        assert {"instagram", "xiaohongshu"} <= platforms
