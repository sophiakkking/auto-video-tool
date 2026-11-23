"use client";

import { useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Job = {
  id: string;
  status: string;
  outputs: { video?: string; cover?: string; transcript?: string; subtitles?: string }[];
};

const TOOLS = [
  { key: "finish", name: "一键成片", desc: "字幕 + 封面 + BGM 打包", ready: true },
  { key: "subtitles", name: "加字幕", desc: "口播视频烧录字幕", ready: true },
  { key: "cover", name: "做封面", desc: "自动生成平台封面图", ready: true },
  { key: "bgm", name: "配音乐", desc: "自动匹配免版税 BGM", ready: false },
  { key: "copy", name: "视频转文案", desc: "转写 + 平台适配文案", ready: true },
] as const;

function fileUrl(jobId: string, name: string) {
  return `${API}/v1/quick/jobs/${jobId}/files/${name}`;
}

export default function QuickPage() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("xiaohongshu");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = (f: File | null) => {
    if (!f) return;
    if (!f.type.startsWith("video/")) {
      setError("请选择视频文件");
      return;
    }
    setError("");
    setFile(f);
    setJob(null);
  };

  const submit = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError("");
    setJob(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", title);
      fd.append("platform", platform);
      const r = await fetch(`${API}/v1/quick/finish`, { method: "POST", body: fd });
      const data = await r.json().catch(() => null);
      if (!r.ok) throw new Error(data?.detail ?? `请求失败: ${r.status}`);
      const j: Job = data;
      setJob(j);
      // 生产 worker 模式下 POST 只返回 quick_processing，轮询到终态
      if (j.status !== "quick_review" && j.status !== "failed") {
        for (;;) {
          await new Promise((res) => setTimeout(res, 2000));
          const sr = await fetch(`${API}/v1/quick/jobs/${j.id}`);
          const sj: Job = await sr.json();
          setJob(sj);
          if (sj.status === "quick_review" || sj.status === "failed") break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const done = job?.status === "quick_review";
  const failed = job?.status === "failed";

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">S4 快速工具</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        {TOOLS.map((t) => (
          <span
            key={t.key}
            className={`rounded-full border px-3 py-1 text-xs ${
              t.ready
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-gray-200 bg-white text-gray-400"
            }`}
          >
            {t.name}
            {t.ready ? "" : " · 开发中"}
          </span>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
        {/* 上传区 */}
        <div
          className={`flex min-h-40 flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors ${
            dragOver ? "border-emerald-400 bg-emerald-50" : "border-gray-300"
          } ${file ? "bg-emerald-50/50" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            pick(e.dataTransfer.files[0] ?? null);
          }}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <>
              <span className="text-3xl">🎬</span>
              <p className="mt-2 text-sm font-medium text-emerald-700">{file.name}</p>
              <p className="mt-1 text-xs text-gray-400">
                {(file.size / 1024 / 1024).toFixed(1)} MB · 点击或拖入替换
              </p>
            </>
          ) : (
            <>
              <span className="text-3xl">🎬</span>
              <p className="mt-2 text-sm font-medium">拖入口播视频,或点击选择</p>
              <p className="mt-1 text-xs text-gray-400">支持 mp4 / mov 等常见格式,≤500MB</p>
            </>
          )}
        </div>

        {/* 参数 */}
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_180px]">
          <label className="block">
            <span className="text-xs text-gray-500">封面标题</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如:冬天第一杯热饮(小红书 ≤20 字)"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-emerald-400"
            />
          </label>
          <label className="block">
            <span className="text-xs text-gray-500">发布平台</span>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-400"
            >
              <option value="xiaohongshu">小红书 (3:4)</option>
              <option value="instagram">Instagram (1:1)</option>
            </select>
          </label>
        </div>

        <button
          onClick={submit}
          disabled={!file || busy}
          className="mt-5 w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {busy ? "生成中…(ASR 转写 + 字幕烧录 + 封面)" : "🚀 一键成片"}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">❌ {error}</p>}
      </div>

      {/* 结果区 */}
      {job && (
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">任务结果</h2>
            <span
              className={`rounded-full px-3 py-1 text-xs ${
                done
                  ? "bg-emerald-50 text-emerald-700"
                  : failed
                    ? "bg-red-50 text-red-600"
                    : "bg-amber-50 text-amber-700"
              }`}
            >
              {done ? "✓ 待审核 quick_review" : failed ? "✗ 失败" : "⏳ 处理中…"}
            </span>
          </div>
          {done && (
            <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_240px]">
              <div>
                <video
                  key={job.id}
                  controls
                  className="aspect-[9/16] w-full rounded-lg bg-black"
                  src={fileUrl(job.id, "finished.mp4")}
                />
              </div>
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-gray-500">封面</p>
                  <img
                    src={fileUrl(job.id, "cover.png")}
                    alt="封面"
                    className="mt-1 aspect-[3/4] w-full rounded-lg border border-gray-100 object-cover"
                  />
                </div>
                <div className="space-y-1 text-sm">
                  <a
                    className="block text-emerald-600 hover:underline"
                    href={fileUrl(job.id, "finished.mp4")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ 成品视频 finished.mp4
                  </a>
                  <a
                    className="block text-emerald-600 hover:underline"
                    href={fileUrl(job.id, "cover.png")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ 封面 cover.png
                  </a>
                  <a
                    className="block text-emerald-600 hover:underline"
                    href={fileUrl(job.id, "subtitles.srt")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ 字幕 subtitles.srt
                  </a>
                  <a
                    className="block text-emerald-600 hover:underline"
                    href={fileUrl(job.id, "transcript.json")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    ⬇ 转写 transcript.json
                  </a>
                </div>
              </div>
            </div>
          )}
          {failed && (
            <p className="mt-3 text-sm text-red-600">任务执行失败,请重试或联系管理员</p>
          )}
        </div>
      )}
    </div>
  );
}
