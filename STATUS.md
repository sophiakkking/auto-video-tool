# PostPilot 进度状态（更新于 2026-11-23 周日）

## 今日完成（2026-11-23）

### Spike 1 口播一键成片 — 全链路跑通并验证 ✅
- `scripts/quick_finish.py testdata/test_video.mp4 --title "冬天第一杯热饮" --platform xiaohongshu`
  → 19.6s 产出 transcript.json / subtitles.srt / finished.mp4 / cover.png（testdata/out/）
- **像素级验证**（Read 工具在此环境看不了图片，改用 PIL 对比）：
  - 字幕烧录：成片 vs 原片同帧对比，顶部 0.0% 差异（无重编码噪声）、底部 21.9%/11.7% 差异
    → ASS+libass 烧录确认成功，且长字幕差异更大（符合预期）
  - 封面：顶部带近白像素为中部 11 倍 + 3 万深色文字像素 → 白带+标题确认画上
- 附带修复：
  - `enable_token_timestamps` 移除（无注意力模型只会刷警告，时间轴由静音分段保证）
  - ASS PlayResX 不再写死 720 → 新增 `_media.video_size()` 取真实宽高
  - **OpenCC 已接入**（opencc-python-reimplemented 装入 venv）：whisper 繁体输出自动转简体
    （`subtitles._normalize_zh`，纯非中文文本原样返回，包缺失时优雅降级）
  - 已回归验证：改后重跑管线 19.3s，字幕/封面均正常

### 快速工具 API 接入 — 代码完成，E2E 待 Docker ⏳
- `POST /v1/quick/finish`：multipart 上传视频 + title/platform/language 表单
  → 本地磁盘存储（Phase 0，KB-9 不入库）→ job.inputs 记路径 → Celery 入队
- `app/workers/tasks.py::quick_finish_task`：加载 job → ASR → 烧录 → 封面 → quick_review
  （同步 DB 桥接用 asyncio.run，异常落 job.status=failed + plan.error）
- 其余 quick 工具（subtitles/cover/bgm/copy）暂时 501（Phase 0 逐个接入）
- 开发期无 Redis：`backend/.env` 设 `CELERY_EAGER=1`（任务请求内同步执行），
  生产/装好 Docker 后改 0 走 worker
- 上传 500MB 限制、失败删孤儿任务、broker 不可达回 503
- 验证状态：导入 OK、路由注册 OK、现有测试 2/2 通过；**E2E（真实上传→成片）需 Postgres 就绪**

## 环境（无管理员，全部用户级安装）
- Python 3.12.8 → C:\Users\Morefun\AppData\Local\Programs\Python\Python312\python.exe
- Node v20.19.0 → C:\Users\Morefun\tools\nodejs\
- ffmpeg 9.1 静态版 → C:\Users\Morefun\tools\ffmpeg\bin\
- venv：postpilot/backend/.venv（sherpa-onnx==2.0.2、opencc-python-reimplemented、setuptools<81、
  ctranslate2==4.6.0、av==19.0.2、faster-whisper==1.2.1【已弃用，勿用】）
- 跑命令前先 `export PATH="$PATH:/c/Users/Morefun/tools/ffmpeg/bin"`
- ⚠️ **Docker 桌面版未装（当前唯一阻塞项）**：安装器在
  C:\Users\Morefun\Downloads\installers\DockerDesktopInstaller.exe，需要用户双击装（管理员 + WSL2）

## 后续队列（按序）
1. **用户装 Docker**（上面安装器）→ `docker compose up -d`（pgvector/redis/minio）→ 后端全接口可用
2. E2E 验证 POST /v1/quick/finish（curl 上传 test_video.mp4，查 quick_review 状态与产物）
3. BGM（QT-3）接免版税曲库 + quick 其余工具逐个接入
4. git 首次提交（未 commit，提交前先问用户）
5. 清理项：Downloads/installers/ 残留（whisper-bin-x64.zip 9 字节 404 文件、7zr.exe 等）

## 用户偏好备忘
- 中文交流；最大权限、自主执行、不要每步都问
- 线框图「有点丑」但可用；界面以 web/ 里 Tailwind 风格为准
- 终端中文乱码是显示问题（GBK 控制台），磁盘文件是正确 UTF-8，用 Read 工具看；
  跑含 emoji 的 Python 输出加 `PYTHONIOENCODING=utf-8`

## 关键坑备忘（Spike 1 沉淀）
- faster-whisper/ctranslate2 在本机 segfault，**勿重试**；ASR 用 sherpa-onnx + whisper-small int8
  （C:\Users\Morefun\tools\sherpa-onnx\models\）
- sherpa 2.x：from_whisper 无 model_type 参数；无注意力模型不要碰 .tokens/.timestamps
- ffmpeg 9：`-filter_complex_script` 已移除；字幕烧录用 ASS + libass 单滤镜
  `subtitles=subs.ass:fontsdir='C\:/Windows/Fonts'`（cwd 切到 ass 所在目录 + 相对文件名）
- 本环境 Read 工具无法显示图片 → 用 ffmpeg 抽帧 + PIL 像素对比验证视觉产物
