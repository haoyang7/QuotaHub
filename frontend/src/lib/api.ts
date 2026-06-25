export interface RefreshSettings {
  auto_refresh: boolean;
  interval_sec: number;
}

export interface ConfigAccount {
  name: string;
  workspace_id: string;
  auth_cookie_masked: string;
  configured: boolean;
  show_rolling: boolean;
  show_weekly: boolean;
  show_monthly: boolean;
}

export interface ConfigOllamaAccount {
  name: string;
  session_cookie_masked: string;
  configured: boolean;
  show_session: boolean;
  show_weekly: boolean;
}

export interface AppConfigResponse {
  refresh: {
    ollama: RefreshSettings;
    opencode_go: RefreshSettings;
  };
  opencode_accounts: ConfigAccount[];
  ollama_accounts: ConfigOllamaAccount[];
}

export function placeholderOpenGoAccounts(opencode_accounts: ConfigAccount[]): QuotaAccount[] {
  return opencode_accounts.map((account, index) => ({
    index,
    name: account.name,
    workspace_id: account.workspace_id,
    success: false,
    updated_at: "",
  }));
}

export function placeholderOllamaAccounts(accounts: ConfigOllamaAccount[]): OllamaQuotaAccount[] {
  return accounts.map((account, index) => ({
    index,
    name: account.name,
    success: false,
    updated_at: "",
  }));
}

export interface QuotaWindow {
  label: string;
  used: number;
  remaining: number;
  total: number;
  unit: string;
  reset_at: string;
  reset_in_sec: number;
  status_text?: string;
  models?: OllamaModelUsage[];
}

export interface OllamaModelUsage {
  model: string;
  requests: number;
  share_percent?: number;
}

export interface QuotaAccount {
  index: number;
  name: string;
  workspace_id?: string;
  success: boolean;
  updated_at: string;
  windows?: QuotaWindow[];
  error?: string;
}

export interface OllamaQuotaAccount {
  index: number;
  name: string;
  plan?: string;
  success: boolean;
  updated_at: string;
  windows?: QuotaWindow[];
  error?: string;
}

async function request<T>(path: string): Promise<T> {
  const resp = await fetch(path);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `请求失败 (${resp.status})`);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  quota: () => request<QuotaAccount[]>("/api/quota"),
  ollamaQuota: () => request<OllamaQuotaAccount[]>("/api/ollama/quota"),
  config: () => request<AppConfigResponse>("/api/config"),
  health: () => request<{ status: string }>("/api/health"),
};
