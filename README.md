# PostPilot

AI 社媒内容工厂：**任意素材进、任意内容出**（文案 / 图片 / 视频），内置平台风格库（Instagram、小红书优先）、分镜审批门、口播一键成片。

设计文档（位于上级目录 `C:\Users\Morefun\`）：

- `social-content-generator-PRD.md` — 产品需求 v0.7（含决策日志）
- `postpilot-wireframes.html` — UI 线框图 v0.1（浏览器打开）
- `postpilot-tech-design.md` — 技术设计 v0.1（架构 / 数据模型 / API / 成本模型 / Phase 0 计划）

## 目录结构

```
postpilot/
├── docker-compose.yml        # Postgres(pgvector) + Redis + MinIO
├── backend/                  # Python 3.12 + FastAPI + Celery
│   ├── app/
│   │   ├── main.py           # 入口：/health、路由挂载、建表
│   │   ├── config.py         # 环境配置（.env）
│   │   ├── db.py             # 异步引擎 + 会话
│   │   ├── models.py         # ORM（技术设计 §4 的全部实体）
│   │   ├── schemas.py        # Pydantic 请求/响应
│   │   ├── api/              # jobs / quick / kb / styles / workspace 路由
│   │   ├── services/         # 素材理解、文案、分镜、渲染、字幕、音乐、RAG（stub）
│   │   ├── workers/          # Celery 应用与任务（stub）
│   │   └── data/             # 平台风格档案种子数据
│   ├── tests/                # 冒烟测试
│   ├── requirements.txt      # 核心依赖（轻量）
│   ├── requirements-dev.txt  # + pytest / httpx
│   ├── requirements-ai.txt   # 重依赖（faster-whisper 等，Phase 0 需要时装）
│   └── .env.example
└── web/                      # Next.js 15 + Tailwind v4
    └── app/                  # 首页壳 + create / quick / storyboard 占位页
```

## 前置安装

本机目前缺以下工具，先装好（脚手架已就绪，装完即可运行）：

1. **Python 3.12** — https://www.python.org/downloads/ （安装时勾选 *Add to PATH*）
2. **Node.js 20+ (LTS)** — https://nodejs.org/ （自带 npm）
3. **Docker Desktop**（可选，跑数据库最省事）— https://www.docker.com/products/docker-desktop/
   - 不用 Docker 的话，需本地安装 PostgreSQL 16 + pgvector 扩展和 Redis

## 快速开始

### 1. 基础设施（数据库 / 队列 / 存储）

```bash
docker compose up -d        # pgvector/pgvector:pg16 + redis:7 + minio
```

> 没有 Docker 时，后端仍可启动（建表失败会被捕获），`/health` 与风格库接口可用；但任务类接口需要数据库。

### 2. 后端（端口 8000）

```bash
cd backend
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

验证：

- 健康检查：http://localhost:8000/health
- 风格库种子数据：http://localhost:8000/v1/styles
- API 文档：http://localhost:8000/docs
- 测试：`python -m pytest -q`

### 3. 前端（端口 3000）

```bash
cd web
npm install
npm run dev      # http://localhost:3000
```

### 4. Worker（Phase 0 接入重任务后）

```bash
cd backend
celery -A app.workers.celery_app worker -Q light,media,heavy -l info
```

## 当前状态与下一步（Phase 0，见技术设计 §11）

| 状态 | 模块 |
|---|---|
| ✅ 可用 | `/health`、`/v1/styles`（种子风格档案）、任务/快速工具/知识库的基础增删查 |
| 🧱 stub（待实现） | services/ 下的素材理解、文案、分镜、渲染、字幕、音乐、RAG；workers/ 任务 |
| 建议第一个 spike | **口播一键成片**（`POST /v1/quick/finish`）：ASR → 字幕烧录 → 封面 → BGM，纯管线、无分镜依赖 |

后端首次启动会自动建表；MVP 为单工作区（自动创建 `demo` 工作区）。
