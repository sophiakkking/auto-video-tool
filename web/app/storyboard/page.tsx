export default function StoryboardPage() {
  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-xl font-bold">S3 分镜审批（骨架）</h1>
        <span className="text-xs text-gray-400">ST-5 快速出片：老用户可跳过本页直接渲染</span>
      </div>
      <div className="mt-6 grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="mb-3 font-semibold">分镜脚本</div>
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="mb-2 rounded-lg border border-dashed border-gray-300 p-3 text-sm text-gray-500">
              镜头 {n} · 2–5s · 画面描述 / 运镜 / 字幕
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="mb-3 font-semibold">定帧图</div>
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="flex h-28 items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-gray-300"
              >
                🖼 {n}
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-400">
            Phase 0 接入：GET/PUT /v1/jobs/{`{id}`}/storyboard · 批准后才渲染（ST-4）
          </p>
        </div>
      </div>
    </div>
  );
}
