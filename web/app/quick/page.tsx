export default function QuickPage() {
  const tools = [
    { name: "🎬 一键成片", desc: "字幕 + 封面 + BGM 打包" },
    { name: "加字幕", desc: "口播视频烧录字幕" },
    { name: "做封面", desc: "自动生成平台封面图" },
    { name: "配音乐", desc: "自动匹配免版税 BGM" },
    { name: "视频转文案", desc: "转写 + 平台适配文案" },
  ];

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">S4 快速工具（骨架）</h1>
      <div className="mt-6 flex flex-wrap gap-3">
        {tools.map((t) => (
          <div key={t.name} className="rounded-xl border border-gray-200 bg-white px-5 py-4">
            <div className="font-semibold">{t.name}</div>
            <div className="mt-1 text-xs text-gray-500">{t.desc}</div>
          </div>
        ))}
      </div>
      <div className="mt-6 flex min-h-40 flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 text-gray-400">
        <span className="text-3xl">🎬</span>
        <p className="mt-2 text-sm">拖入口播视频 → 一键成片</p>
        <p className="mt-1 text-xs">
          Phase 0 接入：POST /v1/quick/finish（ASR → 字幕 → 封面 → BGM）
        </p>
      </div>
    </div>
  );
}
