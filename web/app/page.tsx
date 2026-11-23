import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-52 shrink-0 border-r border-gray-200 bg-white p-4">
        <div className="mb-6 text-lg font-bold">📣 PostPilot</div>
        <nav className="flex flex-col gap-1 text-sm text-gray-600">
          <Link className="rounded px-2 py-1.5 hover:bg-gray-100" href="/create">
            ＋ 新建内容
          </Link>
          <Link className="rounded px-2 py-1.5 hover:bg-gray-100" href="/quick">
            ⚡ 快速工具
          </Link>
          <Link className="rounded px-2 py-1.5 hover:bg-gray-100" href="/storyboard">
            🎬 分镜审批
          </Link>
          <span className="cursor-not-allowed px-2 py-1.5 text-gray-300">📚 内容库</span>
          <span className="cursor-not-allowed px-2 py-1.5 text-gray-300">🎨 品牌套件</span>
          <span className="cursor-not-allowed px-2 py-1.5 text-gray-300">🧠 知识库</span>
          <span className="cursor-not-allowed px-2 py-1.5 text-gray-300">🎭 风格库</span>
        </nav>
      </aside>
      <main className="flex-1 p-8">
        <h1 className="text-2xl font-bold">任意素材进，任意内容出</h1>
        <p className="mt-2 text-sm text-gray-500">
          骨架已就绪 — 后端 <code className="rounded bg-gray-100 px-1">/health</code> 与{" "}
          <code className="rounded bg-gray-100 px-1">/v1/styles</code> 可用，页面逐步接入（Phase 0）。
        </p>
        <div className="mt-6 grid max-w-2xl grid-cols-2 gap-4">
          <Link
            href="/create"
            className="rounded-xl border border-gray-200 bg-white p-6 transition hover:shadow-md"
          >
            <div className="text-lg font-semibold">📥 新建内容</div>
            <div className="mt-1 text-sm text-gray-500">
              完整流水线：素材 → 方案 → 分镜 → 成片（S1–S5）
            </div>
          </Link>
          <Link
            href="/quick"
            className="rounded-xl border border-gray-200 bg-white p-6 transition hover:shadow-md"
          >
            <div className="text-lg font-semibold">⚡ 一键成片</div>
            <div className="mt-1 text-sm text-gray-500">
              口播视频 → 字幕 + 封面 + BGM（S4）
            </div>
          </Link>
        </div>
      </main>
    </div>
  );
}
