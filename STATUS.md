# PostPilot 进度状态（更新于 2026-11-25 周二）

## 今日完成（2026-11-25）

### web quick 页工具选择器 ✅（昨天写好未提交，今天验证+提交 0421777）
- 五个工具入口（finish/subtitles/cover/copy/bgm）卡片式切换，参数随工具联动
- 标题输入仅 finish/cover 可用；bgm 标记 ready；npm build 通过

### BGM 免版税曲库（QT-3）✅
- **曲库来源**：FreePD.com（Kevin MacLeod，CC0 公有领域，原站已关）经 archive.org
  `abook-music-freepd-cc0` 镜像收录 **8 首** → `backend/assets/music/`
  （catalog.json 元数据 + ATTRIBUTION.txt 出处证明）
- moods: neutral / energetic / upbeat / warm / calm / romantic / tech / festive
- **选曲** `music.match_bgm`：track_id 精确换曲 > mood 匹配（命中曲目里优先时长≥视频的最短曲，
  免循环）> 默认曲（Connecting Rainbows）
- **混音** `music.mix_with_video`：音乐 aloop 铺满 + 结尾 2s 渐弱；
  **auto-duck 用 sidechaincompress 以原声为侧链**（人声出现音乐自动压低，无需 ASR）；
  视频流 `-c:v copy` 不重编码，只重编音频 aac；无原声视频直接铺音乐
- **API**：POST /v1/quick/bgm 上线（mood/track 表单参数 + mood 白名单校验）；
  GET /v1/quick/music/tracks 曲库清单（前端换曲）
- **finish 接入 BGM**：一键成片 = 字幕 + 封面 + BGM 混音（QT-4 补齐）
- **前端**：bgm/finish 显示情绪下拉 + 曲目下拉；结果区显示 🎵 曲名/情绪/授权
- **验证**：测试 11/11 通过（新增 test_music.py 6 个单元 + bgm 管线回归 + finish 含 BGM 断言）；
  E2E 烟测 POST /v1/quick/bgm (mood=tech → Meditating Beat) 与 finish（默认曲）均 quick_review，
  产物视频+音频流时长与原片一致；下载路由 200

## 明天队列（按序）
1. 完整流水线（jobs 路由 + material_understanding/content/storyboard/render 任务）Phase 0 实现
2. 可选：Docker Desktop（需升级 Windows）→ 生产形态（Redis worker、MinIO、连接池）
3. 清理项：Downloads/installers 残留（whisper-bin-x64.zip 9 字节、7zr.exe、pg-bin/pgvector 压缩包）

## 环境
- Python 3.12.8 / Node v20.19.0 / ffmpeg 9.1 静态版（均在 C:\Users\Morefun\tools\）
- venv：postpilot/backend/.venv（sherpa-onnx 2.0.2、opencc-python-reimplemented 等）
- 数据库：免安装 PostgreSQL 17.12 + pgvector，`scripts/dev-db.cmd start|stop|status`
  （每次新会话先 start）
- 跑命令前：`export PATH="$PATH:/c/Users/Morefun/tools/ffmpeg/bin"`
- 后端启动：backend 下 `.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload`
- .env 已生成（CELERY_EAGER=1 开发期）；.env 不入库

## 用户偏好备忘
- 中文/英文交流均可；最大权限、自主执行、不要每步都问；尽快推进
- 线框图「有点丑」但可用；界面以 web/ 里 Tailwind 风格为准
- 终端中文乱码是显示问题（GBK 控制台）；跑 Python 打印中文/emoji 加 PYTHONIOENCODING=utf-8
- Read 工具在此环境看不了图片 → ffmpeg 抽帧 + PIL 像素对比验证视觉产物
- 提交消息按用户要求 push 到 GitHub（auto-video-tool）

## 关键坑备忘（Spike 1 沉淀）
- faster-whisper/ctranslate2 在本机 segfault，勿重试；ASR 用 sherpa-onnx + whisper-small int8
- sherpa 2.x：from_whisper 无 model_type 参数；无注意力模型不要碰 .tokens/.timestamps
- ffmpeg 9：`-filter_complex_script` 已移除；字幕烧录用 ASS + libass 单滤镜
  `subtitles=subs.ass:fontsdir='C\:/Windows/Fonts'`（cwd 切到 ass 目录 + 相对文件名）
- SQLAlchemy async 引擎 NullPool（跨 loop 连接会损坏）；Celery eager + task_eager_propagates=True；
  重活统一 `asyncio.to_thread` 跑，服务层 sync 包装供 task 与 route 共用
