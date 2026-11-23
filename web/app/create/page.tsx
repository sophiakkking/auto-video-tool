export default function CreatePage() {
  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-bold">S1 新建内容（骨架）</h1>
      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="col-span-2 flex min-h-64 flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 text-gray-400">
          <span className="text-3xl">⬆</span>
          <p className="mt-2 text-sm">拖入任意素材：文本 / 图片 / 视频 / 音频 / 链接</p>
        </div>
        <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600">
          <p>想要的产出：☐ 文案 ☐ 图片 ☐ 视频</p>
          <p>平台风格：Instagram · 小红书</p>
          <p>内容语言：中文 ▾</p>
          <p className="mt-2 text-xs text-gray-400">
            Phase 0 接入：上传服务 + POST /v1/jobs
          </p>
        </div>
      </div>
    </div>
  );
}
