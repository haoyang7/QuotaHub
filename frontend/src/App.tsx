import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Cloud, RefreshCw, Waves } from "lucide-react";
import {
  api,
  placeholderOllamaAccounts,
  placeholderOpenGoAccounts,
  type AppConfigResponse,
  type OllamaModelUsage,
  type OllamaQuotaAccount,
  type QuotaAccount,
  type QuotaWindow,
  type RefreshSettings,
} from "@/lib/api";
import {
  formatPlanLabel,
  formatResetIn,
  ollamaModelColor,
  ollamaQuotaLabel,
  progressTone,
  quotaLabel,
  usageTone,
} from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

function QuotaWindowRow({ window }: { window: NonNullable<QuotaAccount["windows"]>[number] }) {
  const used = Math.round(window.used * 10) / 10;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-700">{quotaLabel(window.label)}</span>
        <span className={usageTone(window.used)}>
          已用 <span className="font-semibold tabular-nums">{used}%</span>
        </span>
      </div>
      <Progress value={window.used} indicatorClassName={progressTone(window.used)} />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>剩余 {Math.round(window.remaining * 10) / 10}%</span>
        <span>{formatResetIn(window.reset_in_sec)}</span>
      </div>
    </div>
  );
}

function OllamaSegmentedBar({ used, models }: { used: number; models: OllamaModelUsage[] }) {
  const fillWidth = Math.max(0, Math.min(100, used));
  const visibleModels = models.filter((m) => (m.share_percent ?? 0) > 0 || m.requests > 0);

  if (visibleModels.length === 0) {
    return (
      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-slate-400 transition-all duration-500"
          style={{ width: `${fillWidth}%` }}
        />
      </div>
    );
  }

  return (
    <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
      <div className="flex h-full overflow-hidden" style={{ width: `${fillWidth}%` }}>
        {visibleModels.map((model, index) => (
          <div
            key={model.model}
            className="group/segment relative h-full min-w-[2px] shrink-0 cursor-default border-r border-white/80 last:border-r-0"
            style={{
              width: `${Math.max(model.share_percent ?? 0, 0.3)}%`,
              backgroundColor: ollamaModelColor(index),
            }}
            title={`${model.model}: ${model.requests} 次`}
          >
            <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-800 shadow-md group-hover/segment:block">
              <span className="font-medium">{model.model}</span>
              <span className="ml-2 text-slate-500">{model.requests} 次</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OllamaQuotaWindowRow({ window }: { window: QuotaWindow }) {
  const used = Math.round(window.used * 10) / 10;
  const hasModels = Boolean(window.models && window.models.length > 0);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium text-slate-700">{ollamaQuotaLabel(window.label)}</span>
        <span className={usageTone(window.used)}>
          已用 <span className="font-semibold tabular-nums">{used}%</span>
        </span>
      </div>
      {hasModels ? (
        <OllamaSegmentedBar used={window.used} models={window.models!} />
      ) : (
        <Progress value={window.used} indicatorClassName={progressTone(window.used)} />
      )}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>剩余 {Math.round(window.remaining * 10) / 10}%</span>
        <span>{formatResetIn(window.reset_in_sec)}</span>
      </div>
    </div>
  );
}

function filterOllamaWindows(windows: QuotaWindow[] | undefined): QuotaWindow[] {
  if (!windows?.length) return [];
  const weekly = windows.find((w) => w.label === "Weekly");
  const weeklyExhausted = weekly != null && weekly.used >= 100;
  if (weeklyExhausted) {
    return windows.filter((w) => w.label !== "Session");
  }
  return windows;
}

function QuotaLoadingSkeleton({ rows = 2 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="h-4 w-20 animate-pulse rounded bg-slate-200" />
            <div className="h-4 w-16 animate-pulse rounded bg-slate-200" />
          </div>
          <div className="h-2.5 animate-pulse rounded-full bg-slate-200" />
          <div className="flex items-center justify-between">
            <div className="h-3 w-14 animate-pulse rounded bg-slate-100" />
            <div className="h-3 w-24 animate-pulse rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

function OllamaAccountCard({ account, loading }: { account: OllamaQuotaAccount; loading?: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{account.name}</CardTitle>
            <CardDescription className="mt-1">Ollama Cloud</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {!loading && account.plan && <Badge variant="default">{formatPlanLabel(account.plan)}</Badge>}
            <Badge variant={loading ? "default" : account.success ? "success" : "danger"}>
              {loading ? "加载中" : account.success ? "正常" : "异常"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <QuotaLoadingSkeleton rows={2} />
        ) : (
          <>
            {!account.success && account.error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {account.error}
              </div>
            )}
            {filterOllamaWindows(account.windows).map((window) => (
              <OllamaQuotaWindowRow key={window.label} window={window} />
            ))}
            <p className="text-[11px] text-muted-foreground">
              更新于 {new Date(account.updated_at).toLocaleString("zh-CN")}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function OpenGoAccountCard({ account, loading }: { account: QuotaAccount; loading?: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{account.name}</CardTitle>
            <CardDescription className="mt-1 font-mono text-xs">
              {account.workspace_id || "—"}
            </CardDescription>
          </div>
          <Badge variant={loading ? "default" : account.success ? "success" : "danger"}>
            {loading ? "加载中" : account.success ? "正常" : "异常"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <QuotaLoadingSkeleton rows={3} />
        ) : (
          <>
            {!account.success && account.error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {account.error}
              </div>
            )}
            {account.windows?.map((window) => (
              <QuotaWindowRow key={window.label} window={window} />
            ))}
            <p className="text-[11px] text-muted-foreground">
              更新于 {new Date(account.updated_at).toLocaleString("zh-CN")}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function AccountSection({
  title,
  icon,
  description,
  emptyHint,
  successCount,
  totalCount,
  loading,
  onRefresh,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  description: string;
  emptyHint: string;
  successCount: number;
  totalCount: number;
  loading: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
            {icon}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {totalCount > 0 && !loading && (
            <Badge variant={successCount > 0 ? "success" : "warning"}>
              {successCount}/{totalCount} 账号可用
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            刷新
          </Button>
        </div>
      </div>
      {totalCount > 0 ? (
        children
      ) : (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">{emptyHint}</CardContent>
        </Card>
      )}
    </section>
  );
}

const DEFAULT_REFRESH: AppConfigResponse["refresh"] = {
  ollama: { auto_refresh: true, interval_sec: 300 },
  opencode_go: { auto_refresh: true, interval_sec: 60 },
};

export default function App() {
  const [ollamaAccounts, setOllamaAccounts] = useState<OllamaQuotaAccount[]>([]);
  const [openGoAccounts, setOpenGoAccounts] = useState<QuotaAccount[]>([]);
  const [refreshConfig, setRefreshConfig] = useState<AppConfigResponse["refresh"]>(DEFAULT_REFRESH);
  const [configReady, setConfigReady] = useState(false);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [openGoLoading, setOpenGoLoading] = useState(false);
  const [ollamaQuotaReady, setOllamaQuotaReady] = useState(false);
  const [openGoQuotaReady, setOpenGoQuotaReady] = useState(false);
  const [ollamaError, setOllamaError] = useState("");
  const [openGoError, setOpenGoError] = useState("");

  const refreshOllama = useCallback(async () => {
    setOllamaLoading(true);
    try {
      const data = await api.ollamaQuota();
      setOllamaAccounts(data);
      setOllamaError("");
    } catch (e) {
      setOllamaError((e as Error).message);
    } finally {
      setOllamaLoading(false);
      setOllamaQuotaReady(true);
    }
  }, []);

  const refreshOpenGo = useCallback(async () => {
    setOpenGoLoading(true);
    try {
      const data = await api.quota();
      setOpenGoAccounts(data);
      setOpenGoError("");
    } catch (e) {
      setOpenGoError((e as Error).message);
    } finally {
      setOpenGoLoading(false);
      setOpenGoQuotaReady(true);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cfg = await api.config();
        if (cancelled) return;
        setRefreshConfig(cfg.refresh);
        setOllamaAccounts(placeholderOllamaAccounts(cfg.ollama_accounts));
        setOpenGoAccounts(placeholderOpenGoAccounts(cfg.opencode_accounts));
      } catch {
        if (!cancelled) {
          setRefreshConfig(DEFAULT_REFRESH);
        }
      } finally {
        if (!cancelled) {
          setConfigReady(true);
        }
      }
      if (cancelled) return;
      void refreshOllama();
      void refreshOpenGo();
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshOllama, refreshOpenGo]);

  useEffect(() => {
    const settings: RefreshSettings = refreshConfig.ollama;
    if (!settings.auto_refresh) return;
    const id = window.setInterval(refreshOllama, settings.interval_sec * 1000);
    return () => window.clearInterval(id);
  }, [refreshConfig.ollama, refreshOllama]);

  useEffect(() => {
    const settings: RefreshSettings = refreshConfig.opencode_go;
    if (!settings.auto_refresh) return;
    const id = window.setInterval(refreshOpenGo, settings.interval_sec * 1000);
    return () => window.clearInterval(id);
  }, [refreshConfig.opencode_go, refreshOpenGo]);

  const ollamaSuccessCount = ollamaAccounts.filter((a) => a.success).length;
  const openGoSuccessCount = openGoAccounts.filter((a) => a.success).length;
  const totalCount = ollamaAccounts.length + openGoAccounts.length;
  const isEmpty = configReady && totalCount === 0;

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-8 md:px-8">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="h-11 w-11 shrink-0" aria-hidden />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-800">QuotaHub</h1>
            <p className="text-sm text-muted-foreground">Ollama Cloud / OpenCode Go 用量一览</p>
          </div>
        </div>
      </header>

      {(ollamaError || openGoError) && (
        <div className="mb-4 space-y-2">
          {ollamaError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              Ollama：{ollamaError}
            </div>
          )}
          {openGoError && (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              OpenCode Go：{openGoError}
            </div>
          )}
        </div>
      )}

      {!configReady ? (
        <div className="flex flex-1 items-center justify-center py-24 text-muted-foreground">
          <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
          正在加载配置…
        </div>
      ) : isEmpty ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            暂无账号数据。请在项目根目录的 <code className="rounded bg-secondary px-1.5 py-0.5">config.json</code> 中配置
            <code className="rounded bg-secondary px-1.5 py-0.5">ollama_accounts</code> 或
            <code className="rounded bg-secondary px-1.5 py-0.5">opencode_accounts</code>。
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-10">
          <AccountSection
            title="Ollama Cloud"
            icon={<Cloud className="h-4 w-4" />}
            description="5 小时限额 / 周限额"
            emptyHint="未配置 Ollama 账号。请在 config.json 的 ollama_accounts 中填入 session_cookie。"
            successCount={ollamaSuccessCount}
            totalCount={ollamaAccounts.length}
            loading={ollamaLoading}
            onRefresh={refreshOllama}
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {ollamaAccounts.map((account) => (
                <OllamaAccountCard
                  key={`ollama-${account.index}-${account.name}`}
                  account={account}
                  loading={ollamaLoading || !ollamaQuotaReady}
                />
              ))}
            </div>
          </AccountSection>

          <AccountSection
            title="OpenCode Go"
            icon={<Waves className="h-4 w-4" />}
            description="5 小时 / 周 / 月额度"
            emptyHint="未配置 OpenCode Go 账号。请在 config.json 的 opencode_accounts 中填入 auth_cookie。"
            successCount={openGoSuccessCount}
            totalCount={openGoAccounts.length}
            loading={openGoLoading}
            onRefresh={refreshOpenGo}
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {openGoAccounts.map((account) => (
                <OpenGoAccountCard
                  key={`opencode-${account.index}-${account.name}`}
                  account={account}
                  loading={openGoLoading || !openGoQuotaReady}
                />
              ))}
            </div>
          </AccountSection>
        </div>
      )}
    </div>
  );
}
