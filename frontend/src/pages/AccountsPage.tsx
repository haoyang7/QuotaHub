import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Database, Network, Pencil, Plus, Trash2, Waves } from "lucide-react";
import { QuotaWindowRow } from "@/components/quota/QuotaCards";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  api,
  type AdminCPAChannel,
  type CPAQuotaSource,
  type CPAQuotaAccount,
  type OllamaAccount,
  type OpenCodeAccount,
} from "@/lib/api";

type Tab = "opencode" | "ollama" | "cpa";
type ChannelSavePayload = {
  channel: Record<string, unknown>;
  quotaSource: CPAQuotaSource;
  confirmExclusive: boolean;
  sourceNeedsUpdate: boolean;
};
type ConfirmationRequest = {
  title: string;
  description: string;
  details?: string[];
  note?: string;
  confirmLabel: string;
  tone: "warning" | "danger";
  pendingKey: string;
  action: () => Promise<void>;
};

const sleep = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function OpenCodeForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<OpenCodeAccount> & { auth_cookie?: string };
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name || "");
  const [workspaceId, setWorkspaceId] = useState(initial?.workspace_id || "Default");
  const [authCookie, setAuthCookie] = useState(initial?.auth_cookie || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const hasChanges =
    !initial?.id ||
    name.trim() !== initial.name ||
    workspaceId.trim() !== initial.workspace_id ||
    Boolean(authCookie.trim());

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {};
      if (!initial?.id || name.trim() !== initial.name) payload.name = name.trim();
      if (!initial?.id || workspaceId.trim() !== initial.workspace_id) {
        payload.workspace_id = workspaceId.trim();
      }
      if (authCookie.trim()) payload.auth_cookie = authCookie.trim();
      await onSave(payload);
      setAuthCookie("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {initial?.id ? "编辑 OpenCode 账号" : "添加 OpenCode 账号"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="oc-name">名称</Label>
          <Input
            id="oc-name"
            value={name}
            disabled={saving}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="oc-ws">工作区 ID / 名称</Label>
          <Input
            id="oc-ws"
            value={workspaceId}
            disabled={saving}
            onChange={(event) => setWorkspaceId(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="oc-cookie">auth Cookie{initial?.id ? "（留空则不修改）" : ""}</Label>
          <Textarea
            id="oc-cookie"
            value={authCookie}
            disabled={saving}
            autoComplete="new-password"
            onChange={(event) => setAuthCookie(event.target.value)}
            placeholder="auth=Fe26.2**..."
          />
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="flex gap-2">
          <Button
            onClick={() => void submit()}
            disabled={
              saving ||
              !name.trim() ||
              !workspaceId.trim() ||
              (!initial?.id && !authCookie.trim()) ||
              !hasChanges
            }
          >
            {saving ? "保存中…" : "保存"}
          </Button>
          <Button variant="outline" onClick={onCancel} disabled={saving}>
            取消
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function OllamaForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<OllamaAccount> & { session_cookie?: string };
  onSave: (data: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name || "");
  const [sessionCookie, setSessionCookie] = useState(initial?.session_cookie || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const hasChanges =
    !initial?.id || name.trim() !== initial.name || Boolean(sessionCookie.trim());

  const submit = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {};
      if (!initial?.id || name.trim() !== initial.name) payload.name = name.trim();
      if (sessionCookie.trim()) payload.session_cookie = sessionCookie.trim();
      await onSave(payload);
      setSessionCookie("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {initial?.id ? "编辑 Ollama 账号" : "添加 Ollama 账号"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="ol-name">名称</Label>
          <Input
            id="ol-name"
            value={name}
            disabled={saving}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ol-cookie">
            session Cookie{initial?.id ? "（留空则不修改）" : ""}
          </Label>
          <Textarea
            id="ol-cookie"
            value={sessionCookie}
            disabled={saving}
            autoComplete="new-password"
            onChange={(event) => setSessionCookie(event.target.value)}
            placeholder="aid=...; __Secure-session=..."
          />
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="flex gap-2">
          <Button
            onClick={() => void submit()}
            disabled={
              saving ||
              !name.trim() ||
              (!initial?.id && !sessionCookie.trim()) ||
              !hasChanges
            }
          >
            {saving ? "保存中…" : "保存"}
          </Button>
          <Button variant="outline" onClick={onCancel} disabled={saving}>
            取消
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ChannelForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: AdminCPAChannel;
  onSave: (data: ChannelSavePayload) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name || "");
  const [hasCPA, setHasCPA] = useState(Boolean(initial?.cpa_url) || !initial);
  const [cpaUrl, setCPAUrl] = useState(initial?.cpa_url || "");
  const [cpaKey, setCPAKey] = useState("");
  const [hasCPAMP, setHasCPAMP] = useState(Boolean(initial?.cpamp_url));
  const [cpampUrl, setCPAMPUrl] = useState(initial?.cpamp_url || "");
  const [cpampKey, setCPAMPKey] = useState("");
  const [quotaSource, setQuotaSource] = useState<CPAQuotaSource>(initial?.quota_source || "none");
  const [intervalSec, setIntervalSec] = useState(initial?.interval_sec || 1800);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [exclusivePayload, setExclusivePayload] = useState<ChannelSavePayload | null>(null);
  const cpaChanged =
    hasCPA !== Boolean(initial?.cpa_url) ||
    (hasCPA && cpaUrl.trim() !== (initial?.cpa_url || "")) ||
    Boolean(cpaKey.trim());
  const cpampChanged =
    hasCPAMP !== Boolean(initial?.cpamp_url) ||
    (hasCPAMP && cpampUrl.trim() !== (initial?.cpamp_url || "")) ||
    Boolean(cpampKey.trim());
  const hasChanges =
    !initial ||
    name.trim() !== initial.name ||
    cpaChanged ||
    cpampChanged ||
    quotaSource !== initial.quota_source ||
    intervalSec !== initial.interval_sec ||
    (quotaSource === "native_queue" && !initial.queue_enabled);

  const executeSave = async (payload: ChannelSavePayload) => {
    setExclusivePayload(null);
    setSaving(true);
    setError("");
    try {
      await onSave(payload);
      setCPAKey("");
      setCPAMPKey("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const submit = () => {
    if (!Number.isFinite(intervalSec) || intervalSec < 300) {
      setError("同步间隔不能小于 300 秒");
      return;
    }
    if (quotaSource !== "cpamp_snapshot" && !hasCPA) {
      setError("当前额度来源需要配置 CPA 端点");
      return;
    }
    if (quotaSource === "cpamp_snapshot" && !hasCPAMP) {
      setError("CPAMP 快照来源需要配置 CPAMP 端点");
      return;
    }
    if (hasCPA && (!cpaUrl.trim() || (!initial?.cpa_url && !cpaKey.trim()))) {
      setError("CPA 端点需要 URL 和管理密钥");
      return;
    }
    if (hasCPAMP && (!cpampUrl.trim() || (!initial?.cpamp_url && !cpampKey.trim()))) {
      setError("CPAMP 端点需要 URL 和管理密钥");
      return;
    }
    setError("");
    const channel: Record<string, unknown> = {};
    if (!initial || name.trim() !== initial.name) channel.name = name.trim();
    if (!initial || intervalSec !== initial.interval_sec) channel.interval_sec = intervalSec;
    if (!initial || cpaChanged) {
      channel.cpa_endpoint = hasCPA
        ? {
            ...(!initial || cpaUrl.trim() !== initial.cpa_url ? { url: cpaUrl.trim() } : {}),
            ...(cpaKey.trim() ? { management_key: cpaKey.trim() } : {}),
          }
        : null;
    }
    if (!initial || cpampChanged) {
      channel.cpamp_endpoint = hasCPAMP
        ? {
            ...(!initial || cpampUrl.trim() !== initial.cpamp_url
              ? { url: cpampUrl.trim() }
              : {}),
            ...(cpampKey.trim() ? { admin_key: cpampKey.trim() } : {}),
          }
        : null;
    }
    const needsExclusive =
      quotaSource === "native_queue" &&
      (!initial || initial.quota_source !== "native_queue" || !initial.queue_enabled || cpaChanged);
    const payload: ChannelSavePayload = {
      channel,
      quotaSource,
      confirmExclusive: needsExclusive,
      sourceNeedsUpdate: !initial || quotaSource !== initial.quota_source || needsExclusive,
    };
    if (needsExclusive) {
      setExclusivePayload(payload);
      return;
    }
    void executeSave(payload);
  };

  return (
    <>
      <ConfirmationDialog
        open={exclusivePayload !== null}
        title="启用独占 HTTP usage queue？"
        description="QuotaHub 无法自动检测其他消费者。确认后将消费该 CPA 的 usage 事件。"
        details={[
          "QuotaHub 是该 CPA 唯一的 HTTP /usage-queue 消费者。",
          "该 CPA 没有 RESP usage subscriber。",
          "没有其他实例、脚本或程序消费同一 queue。",
        ]}
        note="usage-queue 是破坏性 pop；被其他消费者取走的事件无法恢复。"
        confirmLabel="确认独占并保存"
        tone="warning"
        pending={saving}
        error={error}
        onCancel={() => setExclusivePayload(null)}
        onConfirm={() => exclusivePayload && void executeSave(exclusivePayload)}
      />
      <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {initial ? "编辑 CPA 渠道" : "添加 CPA 渠道"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="cpa-name">渠道名称</Label>
          <Input
            id="cpa-name"
            value={name}
            disabled={saving}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className="space-y-3 rounded-lg border border-slate-200 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">原生 CPA 端点</p>
              <p className="text-xs text-muted-foreground">账号发现与独占 HTTP usage queue</p>
            </div>
            <Switch checked={hasCPA} disabled={saving} onCheckedChange={setHasCPA} />
          </div>
          {hasCPA && <>
          <Label htmlFor="cpa-url">CPA URL</Label>
          <Input
            id="cpa-url"
            value={cpaUrl}
            disabled={saving}
            onChange={(event) => setCPAUrl(event.target.value)}
            placeholder="https://proxy.example.com"
          />
          <Label htmlFor="cpa-key">CPA 管理密钥{initial?.cpa_url ? "（留空则不修改）" : ""}</Label>
          <Input
            id="cpa-key"
            type="password"
            autoComplete="new-password"
            value={cpaKey}
            disabled={saving}
            onChange={(event) => setCPAKey(event.target.value)}
          />
          </>}
        </div>
        <div className="space-y-3 rounded-lg border border-slate-200 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium">CPAMP 端点</p>
              <p className="text-xs text-muted-foreground">只读取已持久化额度快照</p>
            </div>
            <Switch checked={hasCPAMP} disabled={saving} onCheckedChange={setHasCPAMP} />
          </div>
          {hasCPAMP && <>
          <Label htmlFor="cpamp-url">CPAMP URL</Label>
          <Input
            id="cpamp-url"
            value={cpampUrl}
            disabled={saving}
            onChange={(event) => setCPAMPUrl(event.target.value)}
            placeholder="https://cpamp.example.com"
          />
          <Label htmlFor="cpamp-key">CPAMP Admin Key{initial?.cpamp_url ? "（留空则不修改）" : ""}</Label>
          <Input
            id="cpamp-key"
            type="password"
            autoComplete="new-password"
            value={cpampKey}
            disabled={saving}
            onChange={(event) => setCPAMPKey(event.target.value)}
          />
          </>}
        </div>
        <div className="space-y-2">
          <Label>额度来源</Label>
          <TabsList className="h-auto min-h-9 w-full flex-wrap">
            <TabsTrigger active={quotaSource === "none"} onClick={() => setQuotaSource("none")}>
              仅发现账号
            </TabsTrigger>
            <TabsTrigger
              active={quotaSource === "native_queue"}
              onClick={() => setQuotaSource("native_queue")}
            >
              原生 HTTP usage
            </TabsTrigger>
            <TabsTrigger
              active={quotaSource === "cpamp_snapshot"}
              onClick={() => setQuotaSource("cpamp_snapshot")}
            >
              CPAMP 快照
            </TabsTrigger>
          </TabsList>
          <p className="text-xs text-muted-foreground">任一时刻只会访问当前选中的端点。</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="cpa-interval">发现 / 快照同步间隔（秒，最短 300）</Label>
          <Input
            id="cpa-interval"
            type="number"
            min={300}
            value={intervalSec}
            disabled={saving}
            onChange={(event) => setIntervalSec(Number(event.target.value))}
          />
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="flex gap-2">
          <Button
            disabled={
              saving ||
              !name.trim() ||
              !hasChanges
            }
            onClick={submit}
          >
            {saving ? "保存中…" : "保存"}
          </Button>
          <Button variant="outline" onClick={onCancel} disabled={saving}>
            取消
          </Button>
        </div>
      </CardContent>
      </Card>
    </>
  );
}

function AccountSnapshots({
  accounts,
  waitingText,
}: {
  accounts: CPAQuotaAccount[];
  waitingText: string;
}) {
  if (!accounts.length) {
    return <p className="text-sm text-muted-foreground">{waitingText}</p>;
  }
  return (
    <div className="grid gap-2 md:grid-cols-2">
      {accounts.map((account) => (
        <div
          key={account.public_id}
          className="space-y-3 rounded-xl border border-slate-200 p-3 text-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium">{account.account}</span>
            <div className="flex items-center gap-2">
              <Badge variant="default">{account.plan}</Badge>
              {account.stale && <Badge variant="warning">陈旧</Badge>}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {account.success ? "额度缓存正常" : account.error || "等待首次额度事件"}
          </p>
          {account.windows.length > 0 && (
            <div className="space-y-3 border-t border-slate-100 pt-3">
              {account.windows.map((window) => (
                <QuotaWindowRow key={window.label} window={window} />
              ))}
            </div>
          )}
          {account.updated_at && (
            <p className="text-[11px] text-muted-foreground">
              最近成功于 {new Date(account.updated_at).toLocaleString("zh-CN")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function queueStatusLabel(status: AdminCPAChannel["queue_status"]): string {
  const labels: Record<AdminCPAChannel["queue_status"], string> = {
    awaiting_confirmation: "等待独占确认",
    active: "正在消费",
    empty: "队列为空",
    config_disabled: "CPA usage statistics 未开启",
    auth_error: "管理认证失败",
    unsupported: "CPA 版本不支持",
    degraded: "部分事件无法处理",
    disabled: "渠道已停用",
  };
  return labels[status];
}

export default function AccountsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("opencode");
  const [openCodeAccounts, setOpenCodeAccounts] = useState<OpenCodeAccount[]>([]);
  const [ollamaAccounts, setOllamaAccounts] = useState<OllamaAccount[]>([]);
  const [cpaChannels, setCpaChannels] = useState<AdminCPAChannel[]>([]);
  const [editingOpenCode, setEditingOpenCode] = useState<OpenCodeAccount | "new" | null>(null);
  const [editingOllama, setEditingOllama] = useState<OllamaAccount | "new" | null>(null);
  const [editingCPA, setEditingCPA] = useState<AdminCPAChannel | "new" | null>(null);
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const [pageError, setPageError] = useState("");
  const [confirmation, setConfirmation] = useState<ConfirmationRequest | null>(null);
  const pendingRef = useRef(new Set<string>());

  const load = useCallback(async () => {
    const [cfg, cpa] = await Promise.all([api.config(), api.listCPAChannels()]);
    setOpenCodeAccounts(cfg.opencode_accounts);
    setOllamaAccounts(cfg.ollama_accounts);
    setCpaChannels(cpa);
  }, []);

  useEffect(() => {
    void load().catch((error: Error) => setPageError(error.message));
  }, [load]);

  const runPending = useCallback(async (
    key: string,
    operation: () => Promise<void>,
    rethrow = false
  ): Promise<boolean> => {
    if (pendingRef.current.has(key)) {
      if (rethrow) throw new Error("该渠道已有操作正在进行");
      return false;
    }
    pendingRef.current.add(key);
    setPending((current) => ({ ...current, [key]: true }));
    setPageError("");
    try {
      await operation();
      return true;
    } catch (error) {
      setPageError((error as Error).message);
      if (rethrow) throw error;
      return false;
    } finally {
      pendingRef.current.delete(key);
      setPending((current) => {
        const next = { ...current };
        delete next[key];
        return next;
      });
    }
  }, []);

  const pollCPA = useCallback(async (id: string, previousAttempt: string | null | undefined) => {
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      const channels = await api.listCPAChannels();
      setCpaChannels(channels);
      const channel = channels.find((item) => item.id === id);
      if (!channel || !channel.enabled) return;
      if (channel.last_attempt_at && channel.last_attempt_at !== previousAttempt) return;
      await sleep(1000);
    }
  }, []);

  const deleteOpenCode = (id: string) => {
    setPageError("");
    setConfirmation({
      title: "删除 OpenCode 账号？",
      description: "账号配置、额度快照和关联使用记录将被永久删除。",
      note: "此操作无法撤销。建议先确认不再需要该账号的历史数据。",
      confirmLabel: "删除账号",
      tone: "danger",
      pendingKey: `opencode:${id}`,
      action: async () => {
        await api.deleteOpenCodeAccount(id);
        await load();
      },
    });
  };

  const deleteOllama = (id: string) => {
    setPageError("");
    setConfirmation({
      title: "删除 Ollama 账号？",
      description: "账号配置及其额度快照将被永久删除。",
      note: "此操作无法撤销。",
      confirmLabel: "删除账号",
      tone: "danger",
      pendingKey: `ollama:${id}`,
      action: async () => {
        await api.deleteOllamaAccount(id);
        await load();
      },
    });
  };

  const deleteCPA = (id: string) => {
    setPageError("");
    setConfirmation({
      title: "删除 CPA 渠道？",
      description: "该渠道配置、独占确认状态及全部额度快照将被永久删除。",
      note: "删除不会修改 CPA 本身，但此操作无法撤销。",
      confirmLabel: "删除渠道",
      tone: "danger",
      pendingKey: `cpa:${id}`,
      action: async () => {
        await api.deleteCPAChannel(id);
        await load();
      },
    });
  };

  const confirmNativeQueue = (channel: AdminCPAChannel, enableChannel = false) => {
    setPageError("");
    setConfirmation({
      title: enableChannel ? "重新启用渠道并确认独占？" : "启用独占 HTTP usage queue？",
      description:
        "QuotaHub 无法通过管理 API自动检测其他消费者。确认后将开始消费该 CPA 的 usage 事件。",
      details: [
        "QuotaHub 是该 CPA 唯一的 HTTP /usage-queue 消费者。",
        "该 CPA 没有 RESP usage subscriber。",
        "没有其他实例、脚本或程序消费同一 queue。",
      ],
      note: "usage-queue 是破坏性 pop；被其他消费者取走的事件无法恢复。",
      confirmLabel: "确认独占并启用",
      tone: "warning",
      pendingKey: `cpa:${channel.id}`,
      action: async () => {
        if (enableChannel) await api.updateCPAChannel(channel.id, { enabled: true });
        await api.updateCPAQuotaSource(channel.id, {
          source: "native_queue",
          confirm_exclusive: true,
        });
        await load();
        await pollCPA(channel.id, channel.last_attempt_at);
      },
    });
  };

  const confirmCurrentAction = async () => {
    if (!confirmation) return;
    const current = confirmation;
    const completed = await runPending(current.pendingKey, current.action);
    if (completed) setConfirmation(null);
  };

  return (
    <div className="space-y-6">
      <ConfirmationDialog
        open={confirmation !== null}
        title={confirmation?.title || "请确认操作"}
        description={confirmation?.description || ""}
        details={confirmation?.details}
        note={confirmation?.note}
        confirmLabel={confirmation?.confirmLabel || "确认"}
        tone={confirmation?.tone}
        pending={Boolean(confirmation && pending[confirmation.pendingKey])}
        error={confirmation ? pageError : ""}
        onCancel={() => setConfirmation(null)}
        onConfirm={() => void confirmCurrentAction()}
      />
      {pageError && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {pageError}
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs>
          <TabsList className="h-auto min-h-9 flex-wrap">
            <TabsTrigger active={tab === "opencode"} onClick={() => setTab("opencode")}>
              OpenCode Go
            </TabsTrigger>
            <TabsTrigger active={tab === "ollama"} onClick={() => setTab("ollama")}>
              Ollama
            </TabsTrigger>
            <TabsTrigger active={tab === "cpa"} onClick={() => setTab("cpa")}>
              CPA
            </TabsTrigger>
          </TabsList>
        </Tabs>
        {!editingOpenCode && tab === "opencode" && (
          <Button size="sm" onClick={() => setEditingOpenCode("new")}>
            <Plus className="h-4 w-4" />添加账号
          </Button>
        )}
        {!editingOllama && tab === "ollama" && (
          <Button size="sm" onClick={() => setEditingOllama("new")}>
            <Plus className="h-4 w-4" />添加账号
          </Button>
        )}
        {!editingCPA && tab === "cpa" && (
          <Button size="sm" onClick={() => setEditingCPA("new")}>
            <Plus className="h-4 w-4" />添加渠道
          </Button>
        )}
      </div>

      {tab === "opencode" && (
        <div className="space-y-4">
          {editingOpenCode && (
            <OpenCodeForm
              initial={editingOpenCode === "new" ? undefined : editingOpenCode}
              onSave={async (data) => {
                if (editingOpenCode === "new") await api.createOpenCodeAccount(data);
                else await api.updateOpenCodeAccount(editingOpenCode.id, data);
                setEditingOpenCode(null);
                await load();
              }}
              onCancel={() => setEditingOpenCode(null)}
            />
          )}
          <div className="grid gap-3">
            {openCodeAccounts.map((account) => {
              const busy = Boolean(pending[`opencode:${account.id}`]);
              return (
                <Card key={account.id}>
                  <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
                    <div className="flex items-center gap-3">
                      <Waves className="h-5 w-5 text-slate-500" />
                      <div>
                        <p className="font-medium">{account.name}</p>
                        <p className="font-mono text-xs text-muted-foreground">
                          {account.resolved_workspace_id || account.workspace_id}
                        </p>
                        <p className="text-xs text-muted-foreground">{account.auth_cookie_masked}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={account.enabled}
                        disabled={busy}
                        onCheckedChange={(enabled) =>
                          void runPending(`opencode:${account.id}`, async () => {
                            await api.updateOpenCodeAccount(account.id, { enabled });
                            await load();
                          })
                        }
                      />
                      <Badge variant={account.enabled ? "success" : "warning"}>
                        {account.enabled ? "启用" : "停用"}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => navigate(`/admin/accounts/opencode/${account.id}`)}
                      >
                        详情
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        aria-label={`编辑 OpenCode Go 账号 ${account.name}`}
                        title={`编辑 OpenCode Go 账号 ${account.name}`}
                        onClick={() => setEditingOpenCode(account)}
                      >
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        aria-label={`删除 OpenCode Go 账号 ${account.name}`}
                        title={`删除 OpenCode Go 账号 ${account.name}`}
                        onClick={() => deleteOpenCode(account.id)}
                      >
                        <Trash2 className="h-4 w-4 text-rose-600" aria-hidden="true" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {tab === "ollama" && (
        <div className="space-y-4">
          {editingOllama && (
            <OllamaForm
              initial={editingOllama === "new" ? undefined : editingOllama}
              onSave={async (data) => {
                if (editingOllama === "new") await api.createOllamaAccount(data);
                else await api.updateOllamaAccount(editingOllama.id, data);
                setEditingOllama(null);
                await load();
              }}
              onCancel={() => setEditingOllama(null)}
            />
          )}
          <div className="grid gap-3">
            {ollamaAccounts.map((account) => {
              const busy = Boolean(pending[`ollama:${account.id}`]);
              return (
                <Card key={account.id}>
                  <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
                    <div>
                      <p className="font-medium">{account.name}</p>
                      <p className="text-xs text-muted-foreground">{account.session_cookie_masked}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={account.enabled}
                        disabled={busy}
                        onCheckedChange={(enabled) =>
                          void runPending(`ollama:${account.id}`, async () => {
                            await api.updateOllamaAccount(account.id, { enabled });
                            await load();
                          })
                        }
                      />
                      <Badge variant={account.enabled ? "success" : "warning"}>
                        {account.enabled ? "启用" : "停用"}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        aria-label={`编辑 Ollama 账号 ${account.name}`}
                        title={`编辑 Ollama 账号 ${account.name}`}
                        onClick={() => setEditingOllama(account)}
                      >
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        aria-label={`删除 Ollama 账号 ${account.name}`}
                        title={`删除 Ollama 账号 ${account.name}`}
                        onClick={() => deleteOllama(account.id)}
                      >
                        <Trash2 className="h-4 w-4 text-rose-600" aria-hidden="true" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {tab === "cpa" && (
        <div className="space-y-4">
          {editingCPA && (
            <ChannelForm
              initial={editingCPA === "new" ? undefined : editingCPA}
              onSave={async (payload) => {
                const initial = editingCPA === "new" ? undefined : editingCPA;
                await runPending(
                  initial ? `cpa:${initial.id}` : "cpa:new",
                  async () => {
                    let saved: AdminCPAChannel;
                    let syncScheduled = false;
                    if (!initial) {
                      saved = await api.createCPAChannel({
                        ...payload.channel,
                        quota_source: payload.quotaSource,
                        confirm_exclusive: payload.confirmExclusive,
                      });
                      syncScheduled = saved.enabled;
                    } else {
                      const before = { ...payload.channel };
                      const after: Record<string, unknown> = {};
                      let sourceNeedsUpdate = payload.sourceNeedsUpdate;
                      if (payload.quotaSource !== initial.quota_source) {
                        if (
                          initial.quota_source !== "cpamp_snapshot" &&
                          before.cpa_endpoint === null
                        ) {
                          after.cpa_endpoint = null;
                          delete before.cpa_endpoint;
                        }
                        if (
                          initial.quota_source === "cpamp_snapshot" &&
                          before.cpamp_endpoint === null
                        ) {
                          after.cpamp_endpoint = null;
                          delete before.cpamp_endpoint;
                        }
                      }
                      saved = initial;
                      if (Object.keys(before).length > 0) {
                        saved = await api.updateCPAChannel(initial.id, before);
                        syncScheduled ||= Boolean(saved.sync_scheduled);
                        if (
                          sourceNeedsUpdate &&
                          payload.confirmExclusive &&
                          payload.quotaSource === "native_queue" &&
                          initial.quota_source === "native_queue" &&
                          saved.queue_enabled
                        ) {
                          sourceNeedsUpdate = false;
                        }
                      }
                      if (sourceNeedsUpdate) {
                        saved = await api.updateCPAQuotaSource(initial.id, {
                          source: payload.quotaSource,
                          confirm_exclusive: payload.confirmExclusive,
                        });
                        syncScheduled ||= Boolean(saved.sync_scheduled);
                      }
                      if (Object.keys(after).length > 0) {
                        saved = await api.updateCPAChannel(initial.id, after);
                        syncScheduled ||= Boolean(saved.sync_scheduled);
                      }
                    }
                    setEditingCPA(null);
                    await load();
                    if (saved.enabled && syncScheduled) {
                      await pollCPA(saved.id, initial?.last_attempt_at);
                    }
                  },
                  true
                );
              }}
              onCancel={() => setEditingCPA(null)}
            />
          )}
          <div className="grid gap-4">
            {cpaChannels.map((channel) => {
              const busy = Boolean(pending[`cpa:${channel.id}`]);
              return (
                <Card key={channel.id}>
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <Network className="mt-0.5 h-5 w-5 text-slate-500" />
                        <div>
                          <CardTitle className="text-base">{channel.name}</CardTitle>
                          {channel.cpa_url && (
                            <p className="mt-1 text-xs text-muted-foreground">CPA：{channel.cpa_url}</p>
                          )}
                          {channel.cpamp_url && (
                            <p className="mt-1 text-xs text-muted-foreground">CPAMP：{channel.cpamp_url}</p>
                          )}
                          <p className="mt-1 text-xs text-muted-foreground">
                            每 {Math.round(channel.interval_sec / 60)} 分钟同步 · {channel.accounts.length} 个账号
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {busy && <Badge variant="default">处理中…</Badge>}
                        <Switch
                          checked={channel.enabled}
                          disabled={busy}
                          onCheckedChange={(enabled) => {
                            if (enabled && channel.quota_source === "native_queue") {
                              confirmNativeQueue(channel, true);
                              return;
                            }
                            void runPending(`cpa:${channel.id}`, async () => {
                              const saved = await api.updateCPAChannel(channel.id, { enabled });
                              await load();
                              if (enabled && saved.sync_scheduled) {
                                await pollCPA(channel.id, channel.last_attempt_at);
                              }
                            });
                          }}
                        />
                        <Badge variant={channel.enabled ? "success" : "warning"}>
                          {channel.enabled ? "启用" : "停用"}
                        </Badge>
                        <Badge variant="default">
                          {channel.quota_source === "native_queue"
                            ? "原生 HTTP usage"
                            : channel.quota_source === "cpamp_snapshot"
                              ? "CPAMP 快照"
                              : "仅发现账号"}
                        </Badge>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          aria-label={`编辑 CPA 渠道 ${channel.name}`}
                          title={`编辑 CPA 渠道 ${channel.name}`}
                          onClick={() => setEditingCPA(channel)}
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          aria-label={`删除 CPA 渠道 ${channel.name}`}
                          title={`删除 CPA 渠道 ${channel.name}`}
                          onClick={() => deleteCPA(channel.id)}
                        >
                          <Trash2 className="h-4 w-4 text-rose-600" aria-hidden="true" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {channel.quota_source === "native_queue" && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-amber-950">独占 HTTP usage queue</p>
                          <p className="mt-1 text-xs text-amber-800">
                            {queueStatusLabel(channel.queue_status)}。启用前必须确认没有其他 HTTP 消费者和 RESP subscriber。
                          </p>
                        </div>
                        {channel.enabled && !channel.queue_enabled && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy}
                            onClick={() => confirmNativeQueue(channel)}
                          >
                            确认独占并启用
                          </Button>
                        )}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-amber-800">
                        {channel.queue_last_poll_at && (
                          <span>最近轮询：{new Date(channel.queue_last_poll_at).toLocaleString("zh-CN")}</span>
                        )}
                        {channel.queue_last_event_at && (
                          <span>最近事件：{new Date(channel.queue_last_event_at).toLocaleString("zh-CN")}</span>
                        )}
                        {channel.exclusive_confirmed_at && (
                          <span>确认于：{new Date(channel.exclusive_confirmed_at).toLocaleString("zh-CN")}</span>
                        )}
                      </div>
                    </div>
                    )}
                    {channel.quota_source === "cpamp_snapshot" && (
                      <div className="rounded-lg border border-cyan-200 bg-cyan-50 p-3 text-sm text-cyan-950">
                        <div className="flex flex-wrap items-center gap-2">
                          <Database className="h-4 w-4" />
                          <span>CPAMP 只读快照</span>
                          {channel.snapshot_source && (
                            <Badge variant="default">
                              {channel.snapshot_source === "header_snapshots"
                                ? "Header Snapshot 兼容模式"
                                : "Quota Snapshot"}
                            </Badge>
                          )}
                        </div>
                        {channel.last_source_snapshot_at && (
                          <p className="mt-2 text-xs text-cyan-800">
                            最近源快照：
                            {new Date(channel.last_source_snapshot_at).toLocaleString("zh-CN")}
                          </p>
                        )}
                      </div>
                    )}
                    {channel.quota_source === "none" && (
                      <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                        当前只发现 Codex 账号，不采集额度。
                      </p>
                    )}
                    {channel.error && !channel.success && (
                      <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                        {channel.error}
                      </p>
                    )}
                    <AccountSnapshots
                      accounts={channel.accounts}
                      waitingText={
                        channel.quota_source === "cpamp_snapshot"
                          ? "等待 CPAMP 返回已持久化的额度快照。"
                          : channel.quota_source === "native_queue"
                            ? "等待后台发现账号；额度由 usage queue 事件更新。"
                            : "等待后台发现 Codex 账号。"
                      }
                    />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
