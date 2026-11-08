/**
 * IRIS 品牌欢迎页（覆盖 assistant-ui 默认 Welcome 插槽）
 */
export function Welcome() {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl border bg-card text-2xl shadow-sm">
        📊
      </div>
      <h1 className="text-xl font-semibold tracking-tight">
        IRIS · A 股投研多智能体平台
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">
        输入股票代码或名称（如「研究一下 600196 复星医药的投资价值」），
        多 Agent 协作完成 检索 → 数据拉取 → 撰写 → 审查 全流程，生成六章节中文研报。
      </p>
      <div className="mt-2 flex flex-wrap justify-center gap-2 text-xs">
        {["600196 复星医药", "000001 平安银行", "600519 贵州茅台"].map((s) => (
          <span
            key={s}
            className="rounded-full border bg-card px-3 py-1.5 text-muted-foreground"
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
