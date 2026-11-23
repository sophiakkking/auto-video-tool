# PostPilot 进度状态（更新于 2026-11-23 周日）

## 今日完成（2026-11-23）

### Spike 1 口播一键成片 — 全链路跑通并验证 ✅
- CLI：`scripts/quick_finish.py testdata/test_video.mp4 ...` → 19.6s 出 4 产物（testdata/out/）
- 像素级验证：字幕烧录（顶部 0.0% / 底部 21.9% 差异）、封面白带+标题均确认
- OpenCC 繁转简接入、ASS PlayResX 取真实宽高、移除无用的 enable_token_timestamps

### 数据库：免安装 PostgreSQL 17.12 + pgvector 0.8.7 ✅（替代 Docker 方案）
- Windows 10 LTSC 装不了 Docker Desktop（官方不支持 LTSC）→ 改用免安装绿色版，零管理员权限
- 安装位置：C:\Users\Morefun\tools\pgsql（data 在 tools\pgsql\data，日志 pg.log）
- 端口 5432，用户 postpilot / postpilot，库 postpilot，vector 扩展已装
- **启停脚本：postpilot\scripts\dev-db.cmd start | stop | status**（每次新会话先 start）
- 启动方式（脱离 shell）：PowerShell Start-Process 启动 pg_ctl，避免被 Claude 会话杀掉
- 下载残留：Downloads/installers/pg-bin、pgvector（可删）

### API E2E 验证通过 ✅
`POST /v1/quick/finish`（multipart 上传 + title/platform）→ 201，job 状态 quick_review，
outputs 含 transcript/subtitles/video/cover 四条本地路径，产物落盘 storage/quick/{job_id}/out/
- GET /v1/quick/jobs/{id} 可用；API 成片字幕像素验证 PASS（21.9% 底部差异）
- 测试 3/3 通过（新增 tests/test_quick_pipeline.py 管线回归，DB 未启动自动跳过）

### 今天踩掉的坑（重要）
1. **Celery eager 模式**：本机 celery 版本 `task_eager_propagates` 默认 False，任务异常被静默吞掉
   → 已显式开 True
2. **SQLAlchemy async 连接池跨事件循环会损坏连接**（"Future attached to a different loop"）
   → 引擎改 `poolclass=NullPool`（Phase 0 无性能顾虑，生产 worker 进程再调回默认池）
3. **eager 模式架构**：请求内同步跑管线会阻塞事件循环 → 共用管线抽到
   `app/services/quick_pipeline.py`（run_quick_finish / run_quick_finish_sync），
   route 用 `asyncio.to_thread` 跑重活；worker 路径由 Celery 任务薄包装同一函数
4. 重写 quick.py 时曾丢失 GET /jobs/{job_id} 路由 → 已补回并验证

### web quick 页对接完成 ✅（2026-11-23）
- `GET /v1/quick/jobs/{id}/files/{name}`：产物下载（白名单防路径穿越，FileResponse 支持 Range → 视频可拖动）
- `web/app/quick/page.tsx`：拖拽上传 + 标题/平台表单 → POST finish → 轮询状态 → 视频播放器 + 封面 + 4 产物下载
- 验证：下载 200 / 穿越 404 / Range 206；npm build 通过；dev server 烟测 200
- 体验：起 dev-db（数据库已在跑）→ 后端 :8000 → 前端 :3000 → 浏览器开 http://localhost:3000/quick

## Git 状态
- 远程：https://github.com/sophiakkking/auto-video-tool.git（main 跟踪 origin/main）
- 提交：e9c30c0 基线 → e9f3592 E2E 打通 → dd506ba web quick 页对接，均已推送

## 环境
- Python 3.12.8 / Node v20.19.0 / ffmpeg 9.1 静态版（均在 C:\Users\Morefun\tools\）
- venv：postpilot/backend/.venv（sherpa-onnx 2.0.2、opencc-python-reimplemented 等）
- 跑命令前：`export PATH="$PATH:/c/Users/Morefun/tools/ffmpeg/bin"`
- 后端启动：backend 下 `.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload`
- .env 已生成（CELERY_EAGER=1 开发期）；.env 不入库

## 后续队列（按序）
1. ~~web 端 quick 页对接~~ ✅ 已完成
2. BGM（QT-3）接免版税曲库 + quick 其余工具（subtitles/cover/bgm/copy）逐个接入
3. 完整流水线（jobs 路由 + material_understanding/content/storyboard/render 任务）Phase 0 实现
4. 可选：Docker Desktop（需升级 Windows）→ 生产形态（Redis worker、MinIO、连接池）
5. 清理项：Downloads/installers 残留（whisper-bin-x64.zip 9 字节、7zr.exe、pg-bin/pgvector 压缩包）

## 用户偏好备忘
- 中文交流；最大权限、自主执行、不要每步都问；尽快推进
- 线框图「有点丑」但可用；界面以 web/ 里 Tailwind 风格为准
- 终端中文乱码是显示问题（GBK 控制台）；跑 Python 打印中文/emoji 加 PYTHONIOENCODING=utf-8
- Read 工具在此环境看不了图片 → ffmpeg 抽帧 + PIL 像素对比验证视觉产物
- 提交消息按用户要求 push 到 GitHub（auto-video-tool）

## 关键坑备忘（Spike 1 沉淀）
- faster-whisper/ctranslate2 在本机 segfault，勿重试；ASR 用 sherpa-onnx + whisper-small int8
- sherpa 2.x：from_whisper 无 model_type 参数；无注意力模型不要碰 .tokens/.timestamps
- ffmpeg 9：`-filter_complex_script` 已移除；字幕烧录用 ASS + libass 单滤镜
  `subtitles=subs.ass:fontsdir='C\:/Windows/Fonts'`（cwd 切到 ass 目录 + 相对文件名）
