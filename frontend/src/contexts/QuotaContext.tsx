import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  placeholderOllamaAccounts,
  placeholderOpenGoAccounts,
  type AppConfigResponse,
  type OllamaQuotaAccount,
  type QuotaAccount,
  type RefreshSettings,
} from "@/lib/api";
import {
  loadOllamaQuotaCache,
  loadOpenCodeQuotaCache,
  saveOllamaQuotaCache,
  saveOpenCodeQuotaCache,
} from "@/lib/quota-cache";
import { sortOllamaAccountsByQuota, sortOpenCodeAccountsByQuota } from "@/lib/quota-sort";

const DEFAULT_REFRESH: AppConfigResponse["refresh"] = {
  ollama: { auto_refresh: true, interval_sec: 300 },
  opencode_go: { auto_refresh: true, interval_sec: 60 },
};

type QuotaContextValue = {
  ollamaAccounts: OllamaQuotaAccount[];
  openGoAccounts: QuotaAccount[];
  refreshConfig: AppConfigResponse["refresh"];
  configReady: boolean;
  ollamaLoading: boolean;
  openGoLoading: boolean;
  ollamaError: string;
  openGoError: string;
  ollamaHasData: boolean;
  openGoHasData: boolean;
  refreshOllama: () => Promise<void>;
  refreshOpenGo: () => Promise<void>;
  refreshAll: () => Promise<void>;
  reloadRefreshConfig: () => Promise<void>;
};

const QuotaContext = createContext<QuotaContextValue | null>(null);

export function QuotaProvider({ children }: { children: ReactNode }) {
  const [ollamaAccounts, setOllamaAccounts] = useState<OllamaQuotaAccount[]>(() =>
    sortOllamaAccountsByQuota(loadOllamaQuotaCache<OllamaQuotaAccount>() ?? [])
  );
  const [openGoAccounts, setOpenGoAccounts] = useState<QuotaAccount[]>(() =>
    sortOpenCodeAccountsByQuota(loadOpenCodeQuotaCache<QuotaAccount>() ?? [])
  );
  const [refreshConfig, setRefreshConfig] = useState(DEFAULT_REFRESH);
  const [configReady, setConfigReady] = useState(false);
  const [ollamaLoading, setOllamaLoading] = useState(false);
  const [openGoLoading, setOpenGoLoading] = useState(false);
  const [ollamaError, setOllamaError] = useState("");
  const [openGoError, setOpenGoError] = useState("");

  const ollamaHasData = ollamaAccounts.some((a) => a.updated_at || a.error);
  const openGoHasData = openGoAccounts.some((a) => a.updated_at || a.error);

  const refreshOllama = useCallback(async () => {
    setOllamaLoading(true);
    try {
      const data = sortOllamaAccountsByQuota(await api.ollamaQuota());
      setOllamaAccounts(data);
      saveOllamaQuotaCache(data);
      setOllamaError("");
    } catch (e) {
      setOllamaError((e as Error).message);
    } finally {
      setOllamaLoading(false);
    }
  }, []);

  const refreshOpenGo = useCallback(async () => {
    setOpenGoLoading(true);
    try {
      const data = sortOpenCodeAccountsByQuota(await api.quota());
      setOpenGoAccounts(data);
      saveOpenCodeQuotaCache(data);
      setOpenGoError("");
    } catch (e) {
      setOpenGoError((e as Error).message);
    } finally {
      setOpenGoLoading(false);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshOllama(), refreshOpenGo()]);
  }, [refreshOllama, refreshOpenGo]);

  const reloadRefreshConfig = useCallback(async () => {
    try {
      const cfg = await api.config();
      setRefreshConfig(cfg.refresh);
    } catch {
      /* keep current */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const cachedOllama = loadOllamaQuotaCache<OllamaQuotaAccount>();
      const cachedOpenGo = loadOpenCodeQuotaCache<QuotaAccount>();
      try {
        const cfg = await api.config();
        if (cancelled) return;
        setRefreshConfig(cfg.refresh);
        if (!cachedOllama?.length) {
          setOllamaAccounts(sortOllamaAccountsByQuota(placeholderOllamaAccounts(cfg.ollama_accounts)));
        }
        if (!cachedOpenGo?.length) {
          setOpenGoAccounts(sortOpenCodeAccountsByQuota(placeholderOpenGoAccounts(cfg.opencode_accounts)));
        }
      } catch {
        if (!cancelled) setRefreshConfig(DEFAULT_REFRESH);
      } finally {
        if (!cancelled) setConfigReady(true);
      }
      if (!cancelled) {
        void refreshAll();
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const settings: RefreshSettings = refreshConfig.ollama;
    if (!settings.auto_refresh) return;
    const id = window.setInterval(() => void refreshOllama(), settings.interval_sec * 1000);
    return () => window.clearInterval(id);
  }, [refreshConfig.ollama, refreshOllama]);

  useEffect(() => {
    const settings: RefreshSettings = refreshConfig.opencode_go;
    if (!settings.auto_refresh) return;
    const id = window.setInterval(() => void refreshOpenGo(), settings.interval_sec * 1000);
    return () => window.clearInterval(id);
  }, [refreshConfig.opencode_go, refreshOpenGo]);

  const value = useMemo(
    () => ({
      ollamaAccounts,
      openGoAccounts,
      refreshConfig,
      configReady,
      ollamaLoading,
      openGoLoading,
      ollamaError,
      openGoError,
      ollamaHasData,
      openGoHasData,
      refreshOllama,
      refreshOpenGo,
      refreshAll,
      reloadRefreshConfig,
    }),
    [
      ollamaAccounts,
      openGoAccounts,
      refreshConfig,
      configReady,
      ollamaLoading,
      openGoLoading,
      ollamaError,
      openGoError,
      ollamaHasData,
      openGoHasData,
      refreshOllama,
      refreshOpenGo,
      refreshAll,
      reloadRefreshConfig,
    ]
  );

  return <QuotaContext.Provider value={value}>{children}</QuotaContext.Provider>;
}

export function useQuota() {
  const ctx = useContext(QuotaContext);
  if (!ctx) throw new Error("useQuota must be used within QuotaProvider");
  return ctx;
}
