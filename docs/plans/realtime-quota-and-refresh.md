# Realtime Codex Quota, Manual Refresh, And Plan-Upgrade Correctness

```yaml
status: complete
current_milestone: null
last_completed_milestone: M7
next_action: 全部完成；待用户审阅后提交
last_updated: 2026-08-29
branch: master
head: 7715ae4351063120982af26ffaff8307db6436e1
base_version: 0.3.4
changed_files:
  - backend/app/db.py
  - backend/app/cpa_queue.py
  - backend/app/cpa_quota.py
  - backend/app/cpamp_quota.py
  - backend/app/logging_config.py
  - backend/app/main.py
  - backend/app/quota_sync.py
  - backend/tests/test_db.py
  - backend/tests/test_codex_signals.py
  - backend/tests/test_cpamp_quota.py
  - backend/tests/test_api_refresh.py
  - backend/tests/test_api_cpa.py
  - backend/tests/test_cpa_quota.py
  - frontend/src/lib/api.ts
  - frontend/src/pages/AccountsPage.tsx
  - docs/plans/realtime-quota-and-refresh.md
focused_tests:
  - "M1 plan/discovery/snapshot: 12 passed"
  - "M1 test_db+cpa_sync+cpa_queue: 59 passed"
  - "M2 test_codex_signals: 27 passed"
  - "M2 test_cpa_quota+cpamp_quota+cpa_queue: 64 passed"
  - "M3 cpa_sync+cpamp_quota+quota_snapshots: 45 passed"
  - "M3 test_db: 30 passed"
  - "M4 test_api_cpa+cpa_queue: 32 passed"
  - "M4 test_api_refresh: 17 passed"
  - "M6 test_db+api_cpa+cpa_quota+cpamp_quota: 117 passed"
full_verification:
  - "基线后端全量: 165 passed in 4.58s"
  - "M1+M2 合并后全量: 200 passed in 5.49s"
  - "M3+M4 合并后全量: 229 passed in 6.54s"
  - "M5+M6 合并后端全量: 260 passed in 4.60s"
  - "M5 前端 tsc --noEmit + vite build: exit 0, 1763 模块"
  - "P1 修复后后端全量: 272 passed in 7.05s"
  - "浏览器验收：CPAMP 两列、刷新交互、移动端无横向溢出"
  - "Docker 验收：health、SPA、公开 API、管理员登录/会话均通过"
  - "Trivy 镜像漏洞扫描：MEDIUM/HIGH/CRITICAL 为 0"
blockers: []
```

本文件是本轮改造的实现与交接依据���它不得包含管理员令牌、Fernet 密钥、Cookie、
真实账号标识或抓取到的上游私有响应。

上游依据来自本地检出的两个仓库，行号对应检出时的状态：

- `/Users/yanghao/PycharmProjects/CLIProxyAPI`（CPA）
- `/Users/yanghao/PycharmProjects/CPA-Manager-Plus`（CPAMP）

## 背景与问题

三个问题，同一条数据链：

1. **CPAMP 接入用的是快照，不够实时。** `cpamp_snapshot` 读
   `POST /v0/management/quota-snapshots/query`，那是 CPAMP Manager Server
   SQLite 里落库的历史观测，比 CPA 内存中的当前值多一跳延迟。
2. **Ollama 与 CPA 没有任何手动刷新入口。** 只能等调度周期。
3. **账号从 Plus 升级到 Pro 后套餐统计错误。** 已复现，见下。

以及一项新增需求：

4. **账号工作台。** 对标 CPAMP `/accounts` 页面，**只做「凭证/账号」与
   「额度信息」两列**，凭证/账号全脱敏。它与前三项共用同一条 auth-files
   数据链 —— 现在 QuotaHub 每周期都在调该接口，却只取了身份与套餐两个字段，
   其余整个 entry 被丢弃。

## 上游事实（已验证）

### `/v0/management/auth-files` 携带实时额度

- CPAMP 不自行处理该路径，fallthrough 到 `proxyHandler.Management` 转发给 CPA
  （`CPA-Manager-Plus/apps/manager-server/internal/http/router/router.go:113`）。
  因此通过 CPAMP 端点调用得到的是 **CPA 进程内存中的当前状态**。
- 每个 entry 带 `quota` 字段（`CLIProxyAPI/internal/api/handlers/management/auth_files.go:347`）：
  - `quota.observed_at`
  - `quota.signals`：header 名 → 值的字典
- 仅 codex / claude 提供观测（`CLIProxyAPI/sdk/cliproxy/auth/quota_signals.go:17`）。
- 观测写入点在每次请求的结果上报路径上，成功与失败都刷新，并 `m.persist()` 落盘
  （`CLIProxyAPI/sdk/cliproxy/auth/conductor_cooldown.go:913`）。CPA 重启不丢。
- 快照式**整体替换**而非合并（`quota_signals.go:26` 注释与
  `mergeQuotaObservation`），所以不会残留过期水位。

### signals 的键空间

`collectQuotaSignals`（`quota_signals.go:92`）按 provider 白名单收集，键为
`http.CanonicalHeaderKey` 规范化后的形式（如 `X-Codex-Primary-Used-Percent`）。

基础窗口（`isQuotaSignalHeaderForProvider` 明确列出）：

- `x-codex-plan-type`、`x-codex-active-limit`、`x-codex-credits-*`
- `x-codex-allowed`、`x-codex-limit-reached`
- `x-codex-primary-*`、`x-codex-secondary-*`，其中 `*` 为
  `used-percent`、`window-minutes`、`reset-after-seconds`、`reset-at`

额外限额（additional rate limits）**不是固定列表**，按后缀标记匹配
（`quota_signals.go:200-214`）。两种拼写并存：

- HTTP 路径：`x-codex-<shortname>-primary-used-percent`（如 `x-codex-bengalfox-...`）
- WebSocket 路径：`x-codex-additional-<limit>-primary-used-percent`

命名段由上游控制，不可枚举。因此解析必须按**模式 + 时长**判定，不能按名字白名单。

约束：最多 64 个 header（`maxQuotaSignalHeaders`），值最长 512 字符
（`maxQuotaSignalValue`）。超限时按 `quotaSignalRetentionRank` 截断，
`x-codex-additional-*` 排在第 5 档，是**最先被丢弃**的一类。

### 套餐的两个来源，权威性不同

- `id_token.plan_type`：登录时签发的 JWT 声明，**账号升级后不会变，直到重新授权**。
  QuotaHub 现在 `cpa_quota.py:132 _resolve_cpa_plan` 只读这个。
- `quota.signals["x-codex-plan-type"]`：来自最近一次真实响应，带 `observed_at`。

上游自己的优先级可印证：
`CPA-Manager-Plus/apps/web/src/utils/quota/providerRequests.ts:521`
是 `planType = planTypeFromUsage ?? planTypeFromFile`，实时值压过文件值。
`resolveCodexPlanType`（`resolvers.ts:70`）只读凭据文件，是弱源。

### 边界与风险（如实记录）

- CPAMP 自己的前端**没有消费** `auth-files.quota.signals`（全仓搜索零引用）。
  它走 `api-call` + `wham/usage`（实时，用户手动触发）和 Manager Server SQLite。
  该字段是 CPA 侧的正规管理响应，但属于上游面板未自用的路径，
  兼容性不如 `quota-snapshots/query` 经过验证。**必须按兼容性敏感解析器对待。**
- `/v0/management/api-call` 与 ChatGPT `wham/usage` 仍然禁止调用。本方案不触碰。
- auth-files 是被动观测：能拿到「CPA 当前掌握的最新值」，
  **不能**主动逼一个长期闲置的账号去上游刷新。`observed_at` 必须暴露给用户判断新鲜度。

## Bug 复现（plus → pro）

通过真实 db 层执行升级场景，输出：

```
[baseline Plus + success]      public_plan=['Plus']     accounts_table=['Plus']
[key 轮换 + 发现 Pro 20x]       public_plan=['Pro 20x']  accounts_table=['Plus']
[切 source=none + 发现 Pro20x]  public_plan=['Plus']     accounts_table=['Plus']
```

三处根因：

1. `db.py:2032` `_upsert_cpa_account`：
   `plan = CASE WHEN plan = '未知套餐' THEN ? ELSE plan END`
   → `cpa_accounts.plan` 一旦有值就**永久冻结**，无任何路径可纠正。
2. `db.py:2336` `prepare_cpa_channel_discovery`：
   `plan = CASE WHEN last_success_at IS NULL OR plan = '未知套餐' THEN ? ELSE plan END`
   → 有过一次成功采集后，发现流程再也无法修正套餐。
3. `db.py:2822` `list_cached_cpa_channels` 的 LEFT JOIN 要求
   `s.source_mode = c.quota_source`。`quota_source='none'` 永远匹配不到快照行，
   只能回退 `a.plan AS discovered_plan`，即上面那个冻结值。
   换端点、换来源、采集持续失败时同样回退。

`analytics.py:156 aggregate_cpa` 的 `plans` 分布与 Overview 页 badge 计数
（`OverviewPage.tsx:186`）因此统计错误。

M17 加入 1 与 2 是**有意为之**（`test_db.py:622`
`test_discovery_does_not_overwrite_successful_quota_plan` 锁死了该行为），
理由是「auth-files 的套餐不如额度响应可靠」。该判断本身正确 —— `id_token` 确实是
弱源 —— 但实现用「先到先得」代替了「按时间仲裁」，于是冻住了新值、保下了旧值。

## 决策

- CPAMP 采集改为**只用 auth-files**，`quota-snapshots/query` 与 `header-snapshots`
  降为兼容回退。Monthly 与其他额外窗口通过解析 additional 前缀获得。
- 刷新为**同步语义**：POST 后当场采集，拿到新快照再返回。
- 套餐按 **`plan_observed_at` 仲裁**，不再用先到先得冻结。
- 不新增 quota_source 枚举值，`cpamp_snapshot` 保留原名，仅替换实现。
- 账号工作台**只做「凭证/账号」与「额度信息」两列**，其余对标列不做。
  凭证/账号**保持现有脱敏边界不变**：上游身份字段一律不入库、不入 API。
- 账号工作台**不做任何写操作**：不上传/编辑/禁用/删除凭证，不做 OAuth 登录、
  批量操作、巡检触发。QuotaHub 保持只读仪表盘定位。

## 里程碑

### M1 — plus→pro 套餐仲裁（不依赖后续里程碑）

行为：

- `cpa_accounts` 与 `cpa_quota_snapshots` 增加 `plan_observed_at TEXT`，
  幂等迁移（`PRAGMA table_info` + `ALTER TABLE ADD COLUMN`），历史行为 NULL。
- 写入规则统一为：
  - 已存 plan 为 `未知套餐`，或已存 `plan_observed_at IS NULL` → 接受新值；
  - 否则仅当 `新 observed_at >= 已存 plan_observed_at` 时覆盖。
- 发现流的套餐分两级强度：
  - `quota.signals["x-codex-plan-type"]` 带 `quota.observed_at` → 强源，参与仲裁；
  - `id_token.plan_type` 无时间戳 → 弱源，`plan_observed_at` 写 NULL，
    仅在已存为 `未知套餐` 时生效。**这样保留了 M17 的原意。**
- 解冻 `db.py:2032` 与 `db.py:2336` 两处 CASE，改为上述仲裁。
- `_upsert_cpa_account` 同步接受 `plan_observed_at`。

测试（先写，应失败）：

- 纯发现渠道（`quota_source='none'`）在账号升级后能反映新套餐。
- 端点轮换后旧 revision 的快照行不再让公开数据回退到旧套餐。
- 更旧的观测不覆盖更新的套餐（保留 M17 语义）。
- 无时间戳的 `id_token` 套餐不覆盖已知套餐。
- 遗留数据库升级测试：老表 + 老行，迁移后首次强源观测能纠正套餐。

需要改写的既有测试：`test_db.py:622`。改为「更旧的发现结果不覆盖」，
并新增「更新的观测能覆盖」的对照用例。

### M2 — auth-files 实时额度解析器

行为：

- `cpa_quota.py` 的 `CPAAuthAccount` 与 `cpamp_quota.py` 的 `CPAMPAccount`
  增加 `quota_observed_at: str` 与 `quota_signals: dict[str, str]`。
  `parse_auth_files` / `parse_cpamp_auth_files` 保留 `entry["quota"]`，
  键通过 `cpa_queue.py:114 _header_values` 归一化为小写。
- 新增 `codex_headers.py`（或并入 `cpa_queue.py`）通用窗口解析：
  - 枚举所有匹配 `x-codex-(?P<ns>.*-)?(primary|secondary)-used-percent` 的键，
    得出命名空间集合。空命名空间为基础窗口。
  - 排除 `x-codex-code-review-` 命名空间（属于独立功能，不是账号通用额度）。
  - 每个 `(命名空间, primary|secondary)` 走现有 `_parse_window` 的逻辑
    （泛化为接受任意前缀），沿用其 `used-percent` / `window-minutes` /
    `reset-after-seconds` / `reset-at` 字段与钳位规则。
  - 窗口标签由 `window-minutes` 时长判定，复用 `cpa_queue.py:165 _window_label`
    （≤6h → 5h Rolling，≤10d → Weekly，否则 Monthly）。**不按命名空间名字判定**，
    因为命名段由上游控制且不可枚举。
  - 同一 label 冲突时：基础窗口优先；其次优先 `x-codex-active-limit`
    指向的命名空间；再次按命名空间名字典序，保证确定性。
- `x-codex-limit-reached` / `x-codex-allowed` 为真时的处理：不改写 `used`，
  仅作为附加字段记录，避免与百分比来源冲突。

测试（sanitized fixtures，禁止真实响应）：

- 仅基础 primary/secondary → 两个窗口，标签正确。
- HTTP 拼写 `x-codex-<shortname>-primary-*` 且 `window-minutes` 为月级
  → 产出 Monthly 窗口。
- WebSocket 拼写 `x-codex-additional-<limit>-primary-*` → 同上。
- 基础窗口与 additional 窗口标签冲突 → 基础胜出。
- `x-codex-code-review-*` 被忽略。
- signals 被上游截断（缺 `window-minutes` 或缺两种 reset）→ 该窗口整体丢弃，
  不产出半截数据；其余窗口不受影响。
- 空 signals / 非 codex provider → 无窗口，走 M3 的回退。

### M3 — CPAMP 采集链替换

行为：

- `quota_sync.py:648 collect_cpamp_channel` 主路径改为：
  一次 auth-files 调用同时完成账号发现与额度解析，逐账号写快照。
- `observed_at` 取 `quota.observed_at`；staleness 沿用
  `cpamp_quota.py:19 HEADER_SNAPSHOT_MAX_AGE`（6 小时）与
  `HEADER_SNAPSHOT_FUTURE_TOLERANCE`（5 分钟）。
- 回退链（保留既有实现，仅降级为回退）：
  1. auth-files 无 `quota` 字段（CPA 版本过旧）→ `quota-snapshots/query`
  2. `quota-snapshots/query` 返回 404/405 → `header-snapshots`
  3. 发现本身失败 → 沿用现有 `_stored_cpamp_accounts` + header 回退
- `snapshot_source` 新增取值 `auth_files`，需在
  `logging_config.py` 的 `_ALLOWED_FIELDS` / 事件表登记后才能写日志。
- 单个账号解析失败不影响同渠道其他账号（沿用按账号失败隔离约定）。

测试：

- 主路径成功时不再发起 `quota-snapshots/query` 请求（patch 客户端断言零调用）。
- CPA 无 `quota` 字段时正确回退到 query，再 404 回退到 header。
- 观测超过 6 小时标记 stale，保留上一次成功值。
- 401/403 仍然是认证失败，绝不写成额度为零。

### M4 — 同步手动刷新

行为：

- 新增三个路由，均带 `Depends(require_csrf)`：
  - `POST /api/admin/accounts/opencode/{account_id}/refresh`
  - `POST /api/admin/accounts/ollama/{account_id}/refresh`
  - `POST /api/admin/cpa/channels/{channel_id}/refresh`
- 实现照搬 `main.py:599 usage_sync` 的租约模式：进程内锁 →
  `SchedulerLease(QUOTA_LEASE_NAME, owner_id=uuid4())` → `acquire()` 失败返回
  409「额度采集正在进行」→ 调用对应的单个 `collect_*` → `finally: release()`。
  `collect_due_quotas` 是每轮 acquire/release（`quota_sync.py:975` / `:1152`），
  因此周期之间可以抢到租约。
- CPA 渠道的 `quota_source == "native_queue"` 时改用 `cpa-usage-queue` 租约，
  语义为「立刻执行一轮队列消费」。仍需已有的 `exclusive_confirmed_at`；
  未确认独占的渠道返回 409 并说明原因，**不得**绕过独占确认。
- `quota_source == "none"` 的渠道刷新 = 执行一次账号发现（M2 之后它同时带回额度）。
- 返回体：刷新后的快照 DTO + `observed_at`，便于前端直接渲染新鲜度。
- 新增日志事件与字段需先在 `logging_config.py` 登记。

测试：

- 后台轮次持有租约时刷新返回 409，且不发起上游请求。
- 刷新成功后返回的快照即为新写入的那一条。
- 未确认独占的 native_queue 渠道刷新被拒绝且未 pop 队列。
- 刷新走的是采集路径，读接口仍然零上游请求（沿用现有零网络断言）。

### M5 — 前端

行为：

- `lib/api.ts` 增加三个方法与返回 DTO；这是唯一 fetch 站点，
  路由 / schema / api.ts / 消费方 / 后端契约测试必须同批修改。
- `AccountsPage.tsx` 的 OpenCode、Ollama、CPA 卡片各加刷新按钮，
  复用既有的记录级 pending 锁，禁止并发重复提交。
- 展示 `observed_at` 新鲜度与 stale 标记，让用户能区分
  「CPA 掌握的最新值」与「账号闲置导致的陈旧值」。
- 不新增轮询循环；`QuotaContext` 的 60 秒轮询保持唯一。
- 409 会以纯文本 message 到达（`request<T>` 丢弃状态码），
  文案需自解释，不能依赖状态码判断。

### M6 — 账号工作台（仅凭证/账号 + 额度信息两列）

对标 CPAMP `/accounts`，但**只保留两列**。M2 已经把整个 auth-files entry 拿到手，
本里程碑是纯解析与呈现，**零新增上游请求**。

- **额度信息** —— 已由 M2/M3 交付，本里程碑只负责呈现。
- **凭证/账号** —— 按下表全脱敏后入库。

脱敏映射（左侧为 auth-files 字段，右侧为 QuotaHub 的处理）：

| 上游字段 | 处理 |
|---|---|
| `email` / `account` / `chatgpt_account_id` | 已有 `cpa_quota.py:69 mask_cpa_account` |
| `name`（凭证文件名） | 新增 `mask_auth_file_name`：保留扩展名，`codex-a.json` → `co***a.json`；主名 ≤4 字符 → `c***.json` |
| `auth_index` | **不存原值**。用已有 `locator_hash`（`hmac:v1:…`）的摘要末 6 位十六进制作为短标签（如 `#a3f9c1`），仅供人眼区分行，不可反查 |
| `provider` / `type` | 白名单枚举（`codex` / `claude` / …），未知 → `unknown` |
| `project_id` | 掩码后入库，复用账号掩码规则 |
| 套餐 | 由 M1 的 `plan` + `plan_observed_at` 提供，本里程碑不重复处理 |
| `note` / `label` | **不采集**。用户自由文本，无法保证不含身份 |
| `status` / `status_message` / `disabled` / `unavailable` / `runtime_only` | **不采集**。属于已砍掉的「可用状态」列。且 `cpa_quota.py:155` 已在发现阶段过滤掉禁用与不可用凭证，这些账号根本不会出现 |
| `success` / `failed` / `recent_requests` | **不采集**。属于已砍掉的「最近请求」列 |

持久化：

- 上述字段落在 `cpa_accounts`（发现期属性），与 M1 的 `plan_observed_at` 合并为
  同一批幂等迁移。
- **`list_cached_cpa_channels` 必须区分公开与管理员调用**：新增
  `include_credential_details: bool = False`，只有 `/api/admin/*` 传 `True`。
  公开的 `/api/public/quota` 与 `analytics.build_overview` 保持现有字段集不变，
  否则这些凭证属性会随公开接口泄露给匿名用户。

测试：

- 掩码函数：邮箱、短主名、无扩展名、多点扩展名、超长名、空值。
- `provider` 未知取值降级为 `unknown`。
- 公开 DTO 契约测试：`/api/public/quota` 与 overview 的字段集**不含**任何凭证属性。
- 管理员 DTO 契约测试：字段齐全且无原始 `auth_index`、文件名、note、label。
- SQLite 哨兵扫描：库内无原始文件名、`auth_index`、note、label。

前端：

- `lib/api.ts` 扩展管理员 CPA 账号 DTO；公开 DTO 保持不变。
- `AccountsPage.tsx` 的 CPA 账号卡片固定为两列：左列为掩码凭证/账号，右列为
  套餐、额度窗口与 `observed_at` 新鲜度；不在界面渲染 provider、`auth_tag` 或
  `project_id_masked`。
- 复用既有 `components/ui/` 与 `quota-sort.ts`；不引入新的 UI 依赖。
- 不新增轮询循环。

### M7 — 文档与交付

- 更新 `README.md` 中 CPAMP 一节：说明现在读 auth-files 实时观测，
  快照查询为回退；说明被动观测的含义与 `observed_at` 的作用。
- 更新 `CLAUDE.md`：`cpamp_snapshot` 的描述、新增的刷新端点、
  「无手动上游刷新 API」这条已过期的约定。
- `docs/plans/cpa-admin-quota.md` 第 241 行与第 252 行的决策已被本轮取代，
  在该文件追加一条交接说明指向本文档，不修改其历史记录。
- 版本号三处对齐（`backend/pyproject.toml`、`backend/app/version.py`、
  `frontend/package.json`），`python3 scripts/check-version.py` 通过。

## 不做的事

- 不调用 `/v0/management/api-call`，不请求 ChatGPT `wham/usage`。
  该边界在本轮之后依然成立，只是不再是「无法实时」的理由。
- 不新增 quota_source 枚举值。
- 不改动 native_queue 的独占确认模型。
- 不引入第二个前端轮询循环。
- 上游身份字段（`account_key`、邮箱、文件名、`auth_index`、`note`、`label`、
  `status_message` 原文）继续只存在于采集内存中，不得进入 SQLite、
  API 响应或日志。账号工作台只呈现脱敏派生值。
- 账号工作台不做写操作：不上传、编辑、禁用、删除凭证，不做 OAuth 登录、
  批量操作或巡检触发。不调用 `PATCH /auth-files/status` 与 `/auth-files/fields`。
- **不做「可用状态」「最近请求」「历史用量」三列。** 因此本轮不采集
  `status` / `status_message` / `disabled` / `unavailable` / `success` /
  `failed` / `recent_requests`，也不调用
  `POST /v0/management/monitoring/account-history`。
- 不照搬 CPAMP 的 codex-inspection、quota cooldown、account action queue
  三个子系统。

## 验证

- `cd backend && uv run python -m pytest -q`（基线 165 个用例）
- `cd frontend && pnpm build`（严格 tsc + vite，前端唯一门禁）
- `python3 scripts/check-version.py`
- 遗留数据库升级测试：用旧 schema 建库后跑 `init_db()`，断言列已添加且数据保留
- 零网络断言：patch 网络客户端，确认公开读接口不发起上游请求
- SQLite 与日志哨兵扫描：无原始身份、auth_index、管理密钥、明文凭据

## Handoff Log

### 2026-08-27 — 计划创建

- 完成三项问题的定位与上游取证，未改动任何产品代码。
- plus→pro bug 已通过真实 db 层复现，三处根因均定位到具体行号。
- 已确认 `/v0/management/auth-files` 携带实时 `quota.signals`，
  且 CPAMP 对该路径为透传转发。
- 已确认 additional 限额的两种 header 拼写与后缀匹配规则，
  据此确定「按模式 + 时长判定，不按名字白名单」的解析策略。
- 基线已记录：后端全量 165 passed in 4.58s，无告警。

### 2026-08-27 — 追加账号工作台需求（M6/M7）

- 用户要求照搬 CPAMP `/accounts` 的凭证/账号、可用状态、最近请求、
  历史用量、额度信息五块。
- 取证结论：前四块中的凭证/账号、可用状态（基础版）、最近请求、额度信息
  **全部来自 auth-files 同一响应**，零新增上游请求；只有历史用量需要
  额外调用 CPAMP `monitoring/account-history`。
- 用户决策：保持现有脱敏边界不变（身份字段不入库不入 API）；只读展示，
  不做写操作。
- 据此确定脱敏映射表，并识别出一处会导致隐私回归的风险：
  `list_cached_cpa_channels` 同时服务公开与管理员两条路径，
  必须加 `include_credential_details` 开关，否则凭证属性会泄露到匿名接口。

### 2026-08-28 — 范围最终收敛为两列

- 用户确认：账号工作台**只保留「凭证/账号」与「额度信息」两列**，
  「可用状态」「最近请求」「历史用量」三列不做。
- 据此删除原 M7（可选增量），原 M8 顺延为 M7，里程碑总数为 7。
- M6 相应瘦身：不再采集 `status` / `status_message` / `disabled` /
  `unavailable` / `runtime_only` / `success` / `failed` / `recent_requests`；
  `status_message` 的安全码映射与 `recent_requests` 的时区重建一并取消。
- 附带确认：`cpa_quota.py:155` 已在发现阶段过滤掉禁用与不可用凭证，
  所以砍掉状态字段不会让「本该看见的账号」从列表里消失。
- 待用户审阅本文档。批准后从 M1 开始，先写失败的回归测试。
- 下一条命令（M1 开始后）：
  `cd backend && uv run python -m pytest tests/test_db.py -k plan -q`

### 2026-08-28 — M1 完成（plus→pro 套餐仲裁）

- `db.py` 给 `cpa_accounts` 与 `cpa_quota_snapshots` 加 `plan_observed_at TEXT` 列与
  幂等迁移（`PRAGMA table_info` + `ALTER TABLE`，全新库 CREATE TABLE 也含该列）。
- 4 处 UPDATE/ON CONFLICT（`_upsert_cpa_account`、两处 discovery 快照、
  `record_cpa_quota_snapshot` success/error、`record_cpamp_quota_snapshot`）
  统一按观测时间仲裁 plan：强源（`plan_observed_at` 非空）在 stored 为
  `未知套餐`/NULL/`new_obs >= stored` 时接受；弱源仅填充 `未知套餐`。
- 追加守卫：新 plan 为 `未知套餐` 时永不覆盖非 `未知套餐` 的已存 plan（应对 M2 的
  `_account_from_auth_file` 可能输出强源 `未知套餐`，否则会把 Pro 20x 降级）。
- `test_discovery_does_not_overwrite_successful_quota_plan`（test_db.py:622）未改、
  继续通过，M17 弱源语义保留。新增 8 个回归用例（升级、弱源、更旧强源、
  legacy NULL、未知不降级）。
- `record_cpa_quota_batch` 与 `record_cpa_active_attempt` 仍用
  `plan = excluded.plan`（无仲裁/守卫）—— 前者是 native_queue 写路径，留 M4；
  后者 app 代码无调用方（疑 M13 重写后死代码），暂不动。
- focused: 12 passed / 59 passed；合并全量 200 passed。
- 未触碰 cpa_queue/cpa_quota/cpamp_quota 与公开 DTO。

### 2026-08-28 — M2 完成（auth-files 实时额度解析器）

- `cpa_queue.py` 新增 `parse_codex_quota_signals(headers, observed_at)`：枚举
  `x-codex-(ns-)?(primary|secondary)-used-percent` 键，排除 `x-codex-code-review-`，
  按 `window-minutes` 时长判定 label（不按命名空间名字），label 冲突时基础 >
  active-limit 指向 > 字典序。`_parse_window` 泛化为接受 prefix + remaining 回退。
- `CPAAuthAccount`/`CPAMPAccount` 加 `quota_observed_at`/`quota_signals` 字段；
  `parse_auth_files`/`parse_cpamp_auth_files` 保留 `entry["quota"]`，signals 含
  `x-codex-plan-type` 时覆盖 plan（M1 守卫已防降级）。
- `test_codex_signals.py` 27 用例；现有 64 个 CPA/CPAMP/queue 测试无回归。
- 解析器尚未接入采集链（留 M3）；`list_cpamp_snapshot_identities` 未回填
  `plan_observed_at`（留 M3）。

### 2026-08-28 — M3 完成（CPAMP 采集链替换）

- `collect_cpamp_channel`（quota_sync.py:648）主路径改读 auth-files
  `quota.signals`：发现后把账号拆成 `signal_accounts`（有 signals）与
  `fallback_accounts`（无 signals）。主路径逐账号用 `parse_cpamp_signal_snapshot`
  （cpamp_quota.py 新增，封装 `parse_codex_quota_signals` + 年龄 stale）写
  `auth_files` 快照，含单账号失败隔离；`fallback_accounts` 走既有
  query→header 链。同周期可混合，整渠道回退只在「全无 signals」或「发现失败」。
- `CPAMPAccount` 加 `plan_from_signals` 与 `plan_observed_at` 字段；
  `parse_cpamp_auth_files` 填充。采集侧据此传 `plan_observed_at`：signals 有
  plan-type 且 observed_at 可解析 → 强源，否则 None（弱源，防空串当强源时间戳）。
- `list_cpamp_snapshot_identities`（db.py:1942）SELECT 加 `s.plan_observed_at`
  并回填 `CPAMPDiscoveryAccount`，经 `_stored_cpamp_accounts`/`_cpamp_discovery_account`
  线程化到回退重发现，强源 plan 时间戳不再在发现失败时丢失。
- `snapshot_source`/`quota_source` 为自由文本列（无 CHECK），`auth_files` 作值
  直接用；`log_event` 只校验字段名不校验值，`snapshot_source` 字段名已在
  `_ALLOWED_FIELDS`，故 `logging_config.py` 无需改。
- 新增 12 个用例（test_cpamp_quota 10 + test_db 2），focused 45 + 30，全量 229。

### 2026-08-28 — M4 完成（同步手动刷新端点）

- 新增三个 `Depends(require_csrf)` 路由：
  `POST /api/admin/accounts/opencode/{id}/refresh`、
  `POST /api/admin/accounts/ollama/{id}/refresh`、
  `POST /api/admin/cpa/channels/{id}/refresh`。
  照搬 `usage_sync` 的「进程内锁 → SchedulerLease → acquire(失败 409) → collect_*
  → finally release」模式。collect_* 自身不 acquire 租约，无双租约死锁。
- CPA 按源分派：`native_queue` 用 `cpa-usage-queue` 租约并先校验
  `exclusive_confirmed_at`（未确认 409 且不 pop）；`cpamp_snapshot` 用
  `quota-collection` 调 `collect_cpamp_channel`；`none` 用 `quota-collection`
  调 `collect_cpa_channel`（只发现，额度字段为空属正常）。
- `record_cpa_quota_batch`（db.py:2698）的 `plan = excluded.plan` 换成与
  `record_cpa_quota_snapshot` 一致的仲裁 CASE（`observed_at` 作强源
  `plan_observed_at`，含「未知套餐不降级」守卫）。`record_cpa_active_attempt`
  确认无 app 调用方（死代码），不动。
- logging_config 新增事件 `admin_quota_refresh_completed`/`admin_quota_refresh_failed`
  与字段 `result`。
- 新增 17 用例（test_api_refresh），全量 229。
- **已知局限**：native_queue 刷新不当场 pop 队列——`collect_cpa_channel` 只做
  发现/mapping 刷新，pop 由后台 `cpa_usage_queue_loop` 在租约释放后执行。
  故 native_queue 刷新 POST 返回时额度可能仍是上一轮旧值。要做成当场 pop
  需在 cpa_queue.py 导出单渠道 pop 协程，超出 M4 边界，待决策。
- 前端 `api.ts` 未改（留 M5）。

### 2026-08-28 — M5 完成（前端刷新按钮）

- `lib/api.ts` 加 `refreshOpenCodeAccount`/`refreshOllamaAccount`/`refreshCpaChannel`
  三方法，复用现有 `AdminQuotaAccount`/`OllamaQuotaAccount`/`AdminCPAChannel`
  类型（OpenCode 用 admin 形态而非 PublicQuotaAccount，因后端返回含 account_id）。
- `AccountsPage.tsx` 三卡片加刷新按钮（RefreshCw 图标），复用现有
  `pendingRef`+`pending` per-id 锁禁止并发重复点同一记录；成功写局部 state
  + 展示 updated_at 新鲜度；失败走 `showToast`；不加误导性「已刷新」toast
  （native_queue 靠 updated_at 自然体现）。未动 QuotaContext/缓存/后端。
- 前端唯一门禁：`tsc --noEmit` + `vite build` 均 exit 0（1763 模块）。

### 2026-08-28 — M6 后端完成（账号工作台凭证列）

- `cpa_quota.py` 新增 `mask_auth_file_name`（保留扩展名）、`auth_tag_from_locator`
  （locator_hash 末 6 hex + `#`）、`_normalize_provider`（白名单 codex/claude）；
  `CPAAuthAccount` 加 `auth_file_masked`/`auth_tag`/`provider`/`project_id_masked`，
  `_account_from_auth_file` 填充。`cpamp_quota.py` `CPAMPAccount` 同步 + 透传，
  header 回退 `_account_from_parts` 派生。
- `db.py`：`cpa_accounts` 迁移加 4 列；`CPADiscoveryAccount`/`CPAMPDiscoveryAccount`
  加 4 字段；`_upsert_cpa_account` 写入（UPDATE 用 COALESCE/CASE 保留既有值，
  provider 防止 unknown 覆盖真实值）；`list_cached_cpa_channels`/
  `list_cached_cpamp_channels` 加 `include_credential_details=False` 开关——
  True 时 SELECT 并填 4 字段，False 时完全不取不填。
- `main.py` `_admin_cpa_channel_dict` 传 `include_credential_details=True`
  （单渠道详情）；**admin 列表端点 `list_cpa_channels`(main.py:989) 仍默认 False**
  （批 4 补）；公开路由与 overview 维持 False。公开 DTO 契约测试断言零凭证字段。
- ⚠️ 边界偏离：动了 `quota_sync.py` 的 `_cpa_discovery_account`/
  `_cpamp_discovery_account` 适配器（各 4 行字段透传）——这是 parser→discovery
  的唯一桥梁，不透传则 4 字段恒空、M6 功能失效。纯机械字段透传，未动调度逻辑。
- 新增 30 用例，focused 117，全量 260。SQLite 哨兵断言无原始 fileName/
  auth_index/note/label。
- 遗留：admin 列表端点未带凭证字段（批 4 补一行）。

### 2026-08-28 — M6 前端完成（凭证展示）

- 后端补一行：admin 列表端点 `list_cpa_channels`（main.py:989）传
  `include_credential_details=True`，列表页无需逐渠道拉详情。公开路由与 overview
  仍默认 False。新增契约测试断言列表带 4 字段、公开 DTO 不带。
- 前端 `api.ts` 的 `CPAQuotaAccount` 保留管理员 DTO 的掩码字段；`AccountsPage` 的
  `AccountSnapshots` 最终收敛为两列：左侧只显示 `auth_file_masked` 与账号，右侧
  显示套餐、额度窗口和新鲜度。provider、`auth_tag`、`project_id_masked` 不渲染。
  无新依赖、无新请求。该阶段后端验证为 261 passed，前端 build pass。

### 2026-08-28 — M7 完成（文档与交付）

- `README.md`：CPAMP 一节改为「实时额度观测」（读 `/auth-files` `quota.signals`，
  query/header 降为回退）；顶层描述与 `CPAMP 快照` 来源说明同步；「不提供手动刷新」
  改为管理员可手动触发即时采集。
- `CLAUDE.md`：第 60 行「deliberately no manual upstream-refresh endpoint」改为
  描述三个同步刷新端点；第 70 行 `cpamp_snapshot` 改为 auth-files 主路径 + query/header
  回退；新增 `plan_observed_at` 仲裁与脱敏凭证字段（`include_credential_details` 开关、
  公开 DTO 零凭证）说明。
- `docs/plans/cpa-admin-quota.md`：第 250-252 行后追加「已被 realtime-quota-and-refresh.md
  取代」交接说明，历史记录不改。
- 版本三处对齐 0.3.3 → 0.3.4（`backend/pyproject.toml`、`backend/app/version.py`、
  `frontend/package.json`）；`python3 scripts/check-version.py` 通过。
- M7 阶段验证：后端全量 261 passed in 4.65s；前端 `tsc --noEmit` + `vite build` 通过
  （1763 模块）；版本检查 exit 0。

### 2026-08-29 — P1 修复与发布验收

- 原生队列只把明确的信号套餐标记为强来源，并将 `plan_observed_at` 同步写入
  账号表与快照表；弱来源发现结果不会覆盖强来源套餐。
- OpenCode/Ollama 手动刷新采集失败时返回 HTTP 502，不再返回旧缓存伪装成功。
- 后端全量 `272 passed`；最新 Docker 镜像完成启动、SPA、公开 API、管理员登录/会话
  验收；Trivy 按 CI 的 MEDIUM/HIGH/CRITICAL 规则扫描为 0；UV/source 发布包生成成功。

## 最终交付状态

- 后端：165 → 272 测试，+107，零回归。
- 前端：tsc 严格类型检查 + vite build 通过（唯一门禁）。
- 版本：0.3.4，三处对齐（按项目惯例走补丁版本，非语义化 minor）。
- 已知局限（非阻塞）：native_queue 渠道的同步刷新只重新发现账号、刷新 mapping，
  不当场 pop 队列；额度仍由后台 `cpa_usage_queue_loop` 在租约释放后更新。前端靠
  `updated_at` 自然体现新鲜度，不做误导性承诺。其余四种刷新（OpenCode/Ollama/
  CPAMP/CPA-none）均当场拿到新快照。
