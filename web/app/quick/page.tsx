"use client";

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Job = {
  id: string;
  status: string;
  outputs: {
    video?: string;
    cover?: string;
    transcript?: string;
    subtitles?: string;
    bgm?: { id: string; title: string; moods: string[]; tempo: string; license: string };
  }[];
};

const TOOLS = [
  { key: "finish", name: "一键成片", desc: "字幕 + 封面 + BGM 打包", busy: "ASR 转写 + 字幕烧录 + 封面 + 混音中…", ready: true },
  { key: "subtitles", name: "加字幕", desc: "口播视频烧录字幕", busy: "ASR 转写 + 字幕烧录中…", ready: true },
  { key: "cover", name: "做封面", desc: "自动生成平台封面图", busy: "封面生成中…", ready: true },
  { key: "copy", name: "视频转文案", desc: "转写 + 文案提取", busy: "ASR 转写中…", ready: true },
  { key: "bgm", name: "配音乐", desc: "免版税曲库 + 人声闪避", busy: "匹配 + 混音中…", ready: true },
] as const;

const MOODS = [
  { key: "", label: "自动匹配" },
  { key: "energetic", label: "活力" },
  { key: "upbeat", label: "轻快" },
  { key: "warm", label: "温暖" },
  { key: "calm", label: "舒缓" },
  { key: "romantic", label: "浪漫" },
  { key: "tech", label: "科技" },
  { key: "festive", label: "节庆" },
  { key: "neutral", label: "中性" },
] as const;

type Track = { id: string; title: string; moods: string[]; tempo: string; license: string };

type ToolKey = (typeof TOOLS)[number]["key"];

function fileUrl(jobId: string, name: string) {
  return `${API}/v1/quick/jobs/${jobId}/files/${name}`;
}

export default function QuickPage() {
  const [tool, setTool] = useState<ToolKey>("finish");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("xiaohongshu");
  const [mood, setMood] = useState("");
  const [track, setTrack] = useState("");
  const [tracks, setTracks] = useState<Track[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const current = TOOLS.find((t) => t.key === tool)!;
  const useBgm = tool === "bgm" || tool === "finish";

  useEffect(() => {
    fetch(`${API}/v1/quick/music/tracks`)
      .then((r) => r.json())
      .then((list: Track[]) => setTracks(list))
      .catch(() => setTracks([])); // 曲库接口不可用就只留"自动"
  }, []);

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

  const selectTool = (t: ToolKey) => {
    setTool(t);
    setError("");
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
      if (useBgm) {
        fd.append("mood", mood);
        fd.append("track", track);
      }
      const r = await fetch(`${API}/v1/quick/${tool}`, { method: "POST", body: fd });
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
  const outputs = job?.outputs?.[0] ?? {};
  const needsTitle = tool === "finish" || tool === "cover";

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">S4 快速工具</h1>

      {/* 工具选择器 */}
      <div className="mt-4 grid gap-2 sm:grid-cols-5">
        {TOOLS.map((t) => {
          const active = t.key === tool;
          return (
            <button
              key={t.key}
              type="button"
              disabled={!t.ready}
              onClick={() => selectTool(t.key)}
              className={`rounded-xl border px-3 py-2 text-left transition-colors ${
                active
                  ? "border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500"
                  : t.ready
                    ? "border-gray-200 bg-white hover:border-emerald-300"
                    : "cursor-not-allowed border-gray-200 bg-white opacity-50"
              }`}
            >
              <span className={`block text-sm font-medium ${active ? "text-emerald-700" : "text-gray-700"}`}>
                {t.name}
              </span>
              <span className="mt-0.5 block text-[11px] leading-tight text-gray-400">
                {t.ready ? t.desc : "开发中"}
              </span>
            </button>
          );
        })}
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
            <span className="text-xs text-gray-500">
              封面标题{needsTitle ? "" : "（本工具用不到）"}
            </span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={!needsTitle}
              placeholder="例如:冬天第一杯热饮(小红书 ≤20 字)"
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-emerald-400 disabled:bg-gray-50 disabled:text-gray-400"
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

        {/* BGM 选曲（bgm / finish 共用） */}
        {useBgm && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs text-gray-500">BGM 情绪</span>
              <select
                value={mood}
                onChange={(e) => setMood(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-400"
              >
                {MOODS.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs text-gray-500">指定曲目（可换曲）</span>
              <select
                value={track}
                onChange={(e) => setTrack(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-400"
              >
                <option value="">自动选曲</option>
                {tracks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}（{t.moods.join(" / ")}）
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        <button
          onClick={submit}
          disabled={!file || busy}
          className="mt-5 w-full rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {busy ? current.busy || "生成中…" : `🚀 ${current.name}`}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">❌ {error}</p>}
      </div>

      {/* 结果区 */}
      {job && (
        <ResultPanel job={job} done={done} failed={failed} outputs={outputs} tool={tool} />
      )}
    </div>
  );
}

/** 结果面板：按 outputs 里实际存在的产物渲染 */
function ResultPanel({
  job,
  done,
  failed,
  outputs,
  tool,
}: {
  job: Job;
  done: boolean;
  failed: boolean;
  outputs: {
    video?: string;
    cover?: string;
    transcript?: string;
    subtitles?: string;
    bgm?: { id: string; title: string; moods: string[]; tempo: string; license: string };
  };
  tool: ToolKey;
}) {
  const [copied, setCopied] = useState(false);

  return (
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

      {done && outputs.video && (
        <div className="mt-4">
          <video
            key={job.id}
            controls
            className="mx-auto aspect-[9/16] max-w-sm rounded-lg bg-black"
            src={fileUrl(job.id, "finished.mp4")}
          />
          <p className="mt-2 text-center text-sm">
            <a className="text-emerald-600 hover:underline" href={fileUrl(job.id, "finished.mp4")} target="_blank" rel="noreferrer">
              ⬇ 下载成品视频 finished.mp4
            </a>
          </p>
        </div>
      )}

      {done && outputs.cover && (
        <div className="mt-4 grid gap-4 sm:grid-cols-[240px_1fr] sm:items-start">
          <img
            src={fileUrl(job.id, "cover.png")}
            alt="封面"
            className="w-full rounded-lg border border-gray-100 object-cover"
          />
          <div className="text-sm">
            <p className="text-xs text-gray-500">封面</p>
            <a className="text-emerald-600 hover:underline" href={fileUrl(job.id, "cover.png")} target="_blank" rel="noreferrer">
              ⬇ 下载封面 cover.png
            </a>
          </div>
        </div>
      )}

      {done && (outputs.transcript || outputs.subtitles) && (
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          {outputs.subtitles && (
            <a className="text-emerald-600 hover:underline" href={fileUrl(job.id, "subtitles.srt")} target="_blank" rel="noreferrer">
              ⬇ 字幕 subtitles.srt
            </a>
          )}
          {outputs.transcript && (
            <a className="text-emerald-600 hover:underline" href={fileUrl(job.id, "transcript.json")} target="_blank" rel="noreferrer">
              ⬇ 转写 transcript.json
            </a>
          )}
        </div>
      )}

      {done && outputs.bgm && (
        <p className="mt-4 rounded-lg bg-emerald-50/60 px-3 py-2 text-sm text-emerald-800">
          🎵 BGM: {outputs.bgm.title}（{outputs.bgm.moods.join(" / ")} · {outputs.bgm.license}）
        </p>
      )}

      {done && tool === "copy" && outputs.transcript && (
        <TranscriptPreview jobId={job.id} copied={copied} setCopied={setCopied} />
      )}

      {failed && <p className="mt-3 text-sm text-red-600">任务执行失败,请重试或联系管理员</p>}
    </div>
  );
}

/** copy 工具：拉取转写 JSON，拼出全文 + 一键复制 */
function TranscriptPreview({
  jobId,
  copied,
  setCopied,
}: {
  jobId: string;
  copied: boolean;
  setCopied: (v: boolean) => void;
}) {
  const [text, setText] = useState<string | null>(null);
  const [loadErr, setLoadErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(fileUrl(jobId, "transcript.json"));
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const segs: { text: string }[] = await r.json();
        if (!cancelled) setText(segs.map((s) => s.text).join("\n"));
      } catch (e) {
        if (!cancelled) setLoadErr(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const copyText = async () => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* 剪贴板不可用时忽略 */
    }
  };

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">文案预览（转写全文）</p>
        <button
          type="button"
          onClick={copyText}
          disabled={!text}
          className="rounded-lg border border-emerald-300 px-3 py-1 text-xs text-emerald-700 hover:bg-emerald-50 disabled:border-gray-200 disabled:text-gray-400"
        >
          {copied ? "✓ 已复制" : "📋 复制全文"}
        </button>
      </div>
      {loadErr ? (
        <p className="mt-2 text-sm text-red-600">转写加载失败: {loadErr}</p>
      ) : text === null ? (
        <p className="mt-2 text-sm text-gray-400">加载中…</p>
      ) : (
        <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm leading-relaxed text-gray-700">
          {text}
        </pre>
      )}
    </div>
  );
}
