import { useGraphStore } from "@/store/graphStore";

function fmtPct(v?: string): { text: string; up: boolean } | null {
  if (!v) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return { text: `${n > 0 ? "+" : ""}${n.toFixed(2)}%`, up: n >= 0 };
}

function fmtMarketCap(v?: string): string | null {
  if (!v) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  return `${(n / 1e8).toFixed(0)} 亿`;
}

/**
 * 实时行情小卡：data_collector 完成后拉 /api/stock/{code}/quote 渲染。
 * 数据缺失字段自动隐藏（fail-open）。
 */
export function MarketDataCard() {
  const quote = useGraphStore((s) => s.quote);
  if (!quote) return null;

  const pct = fmtPct(quote.涨跌幅);
  const cap = fmtMarketCap(quote.总市值);

  return (
    <div
      data-slot="iris_quote_card"
      className="mx-auto w-full max-w-3xl px-4 pb-2"
    >
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 rounded-xl border bg-card px-4 py-2.5 text-xs shadow-sm">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[11px] text-muted-foreground">
            {quote.stock_code}
          </span>
          <span className="text-base font-semibold tabular-nums">
            {quote.最新价 ?? "—"}
          </span>
          {pct && (
            <span
              className={
                pct.up
                  ? "font-medium tabular-nums text-red-600 dark:text-red-400"
                  : "font-medium tabular-nums text-emerald-600 dark:text-emerald-400"
              }
            >
              {pct.text}
            </span>
          )}
        </div>
        <div className="hidden gap-x-5 text-muted-foreground sm:flex">
          {quote.今开 && (
            <span>
              今开 <span className="tabular-nums text-foreground">{quote.今开}</span>
            </span>
          )}
          {quote.最高 && quote.最低 && (
            <span>
              波动{" "}
              <span className="tabular-nums text-foreground">
                {quote.最低} – {quote.最高}
              </span>
            </span>
          )}
          {quote.市盈率 && (
            <span>
              PE <span className="tabular-nums text-foreground">{quote.市盈率}</span>
            </span>
          )}
          {cap && (
            <span>
              总市值 <span className="tabular-nums text-foreground">{cap}</span>
            </span>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2 text-[11px] text-muted-foreground">
          {quote.延时 && quote.延时 !== "实时" && (
            <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-600 dark:text-amber-400">
              {quote.延时}
            </span>
          )}
          <span className="max-w-40 truncate" title={quote.data_source}>
            {quote.data_source}
          </span>
        </div>
      </div>
    </div>
  );
}
