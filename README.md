# QuotaHub

QuotaHub 是一个自托管额度看板，支持 OpenCode Go、Ollama Cloud 和多个
CLIProxyAPI（CPA）渠道。CPA 渠道可按部署方式选择原生独占 usage queue 或
CPA-Manager-Plus（CPAMP）只读快照。所有额度先写入 SQLite；浏览器刷新和轮询只读本地快照，
不会直接请求上游。

公开用户只能查看数据概览和账号额度。账号、CPA 渠道、使用记录与采集设置位于独立的
管理员后台。

## 致谢

本项目在 [QuotaHub](https://github.com/lvmiao233/QuotaHub) 基础上扩展，感谢原项目作者的开源贡献。

感谢 [LinuxDo](https://linux.do) 社区佬友们的交流与分享。

OpenCode Go 额度查询功能参考了
[opencode-cc](https://github.com/Kiowx/opencode-cc)（[@Kiowx](https://github.com/Kiowx)）。

## 启动前必填

QuotaHub 启动时必须提供以下两个环境变量；缺失、格式错误或无法解密已有数据时会拒绝启动。

| 变量 | 要求 | 说明 |
|------|------|------|
| `QUOTAHUB_ADMIN_TOKEN` | 至少 32 字符 | 管理员登录令牌，仅保存在部署环境中 |
| `QUOTAHUB_ENCRYPTION_KEY` | Fernet 密钥 | 加密 OpenCode/Ollama Cookie 与 CPA 管理密钥 |

生成示例：

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

请把生成结果放进密码管理器或部署平台的 Secret。主密钥必须长期稳定；丢失后无法恢复已加密凭证。

生产 HTTPS 还应设置：

```bash
QUOTAHUB_COOKIE_SECURE=true
```

本地 HTTP 保持 `false`。管理员 Cookie 使用 `HttpOnly`、`SameSite=Strict`，服务端最长有效 24 小时。

## Docker 部署

使用 Release 镜像：

```bash
docker pull ghcr.io/haoyang7/quotahub:latest
docker run -d --name quotahub \
  -p 28787:8788 \
  -v ./data:/data \
  -e QUOTAHUB_ADMIN_TOKEN='替换为至少32字符的随机令牌' \
  -e QUOTAHUB_ENCRYPTION_KEY='替换为Fernet密钥' \
  -e QUOTAHUB_COOKIE_SECURE=false \
  -e QUOTAHUB_LOG_LEVEL=INFO \
  -e QUOTAHUB_LOG_TIMEZONE=LOCAL \
  ghcr.io/haoyang7/quotahub:latest
```

本地构建：

```bash
cp .env.example .env
# 编辑 .env，填写两个必填 Secret
cp docker-compose.yml.example docker-compose.yml
docker compose up -d --build --force-recreate
```

浏览器打开 `http://localhost:28787`。公开页右上角的管理图标进入 `/admin/login`。

数据目录默认为 `./data`，SQLite 数据库为 `data/quotahub.db`。不要提交 `.env`、`data/`、数据库或真实配置。

## 直接运行

要求 Python 3.11+ 与 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

```bash
export QUOTAHUB_ADMIN_TOKEN='替换为至少32字符的随机令牌'
export QUOTAHUB_ENCRYPTION_KEY='替换为Fernet密钥'
export QUOTAHUB_COOKIE_SECURE=false
export QUOTAHUB_LOG_LEVEL=INFO
export QUOTAHUB_LOG_TIMEZONE=LOCAL
./scripts/start.sh
```

默认监听 `http://127.0.0.1:8788`，数据目录为 `./data`。

通过 Git clone 获取的源码不包含 `frontend/dist`，必须先构建前端：

```bash
cd frontend
corepack enable
corepack pnpm@10.33.0 install --frozen-lockfile
corepack pnpm@10.33.0 build
cd ..
./scripts/start.sh
```

Release 的 UV 包和源码附件已包含 `frontend/dist`，可以配置环境变量后直接运行。

常用环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `QUOTAHUB_DATA` | `./data`，Docker 为 `/data` | SQLite 与运行数据目录 |
| `QUOTAHUB_LISTEN_HOST` | `127.0.0.1` | 监听地址 |
| `QUOTAHUB_LISTEN_PORT` | `8788` | 监听端口 |
| `QUOTAHUB_CONFIG` | 无 | 仅升级时指定旧 `config.json` |
| `QUOTAHUB_COOKIE_SECURE` | `false` | HTTPS 部署时设为 `true` |
| `QUOTAHUB_LOG_LEVEL` | `INFO` | `DEBUG`、`INFO`、`WARNING` 或 `ERROR` |
| `QUOTAHUB_LOG_TIMEZONE` | `LOCAL` | `LOCAL` 使用系统本地时区；`UTC` 使用 `Z` 后缀 |

应用日志以单行文本写入 stdout，由 Docker 或宿主系统负责保存和轮转。实际执行的额度与使用记录
周期会记录调度器、随机运行 ID、渠道/账号内部 ID、任务数量、耗时和结果；没有到期任务的轮询仅在
`DEBUG` 级别出现。日志不会记录 Cookie、管理密钥、管理员令牌、`auth_index`、原始账号或上游响应正文。
Uvicorn 的默认访问日志已关闭，避免其直接输出客户端 IP；管理员登录事件改为记录不可逆的来源 HMAC。

## CPA 渠道与额度来源

管理员后台的「账号管理 → CPA」支持多个渠道。每个渠道可同时保存一组 CPA 端点和一组 CPAMP
端点，但任一时刻只能选择一种额度来源：

- `仅发现账号`：只通过 CPA 的 `/auth-files` 维护脱敏账号，不采集额度；
- `原生 HTTP usage`：发现 CPA 账号并消费独占的 HTTP usage queue；
- `CPAMP 快照`：只访问 CPAMP 已持久化的只读快照。

未选中的端点不会发起请求。渠道同步间隔默认 30 分钟，后端最短 5 分钟。两组管理密钥分别使用
Fernet 加密，API 不会返回密钥、掩码或“已配置”标记。切换来源会立即停止旧来源的新请求；历史
快照仍保留在 SQLite，但 API 只展示当前来源。

### 原生 CPA：独占 HTTP usage queue

QuotaHub 对原生 CPA 只执行两类操作：

- 按发现间隔调用 `GET /v0/management/auth-files`，维护脱敏账号清单；
- 经管理员明确确认后，每 15 秒调用本地管理接口
  `GET /v0/management/usage-queue?count=100`，消费 CPA 已产生的 usage 事件。

QuotaHub **不会**调用 `/v0/management/api-call`、ChatGPT `wham/usage`，也不会把原生 CPA 的
`header-snapshots` 作为额度源。页面刷新不会触发 queue 请求。

### 独占确认是强制安全边界

`usage-queue` 是破坏性 pop：记录被一个 HTTP 消费者读取后即从队列移除。CLIProxyAPI 源码还规定，
一旦存在 RESP usage subscriber，事件会直接广播给 subscriber，不再进入 HTTP queue。因此 QuotaHub
无法通过管理 API 自动证明“没有其他消费者”，必须由部署者在管理员页面确认：

1. QuotaHub 是该 CPA 唯一的 HTTP `/v0/management/usage-queue` 消费者；
2. 该 CPA 没有 RESP usage subscriber；
3. 其他程序、脚本或旧 QuotaHub 实例均未消费同一 queue。

渠道停用、URL 变化或管理密钥变化都会关闭 queue 并清除确认；重新启用后必须再次确认。未确认时
QuotaHub 绝不会调用 `/usage-queue`。

CLIProxyAPI 需要允许 QuotaHub 所在机器或容器访问管理 API，并开启 usage statistics：

```yaml
remote-management:
  allow-remote: true
  secret-key: "使用高强度管理密钥"

usage-statistics-enabled: true
redis-usage-queue-retention-seconds: 300
```

QuotaHub 与 CPA 不在同一容器时，渠道 URL 必须是 QuotaHub 容器能够访问的地址；容器内的
`127.0.0.1` 通常只指向 QuotaHub 自身。请按 Docker 网络、宿主机地址或反向代理的实际拓扑配置，
并限制管理 API 的防火墙访问范围。

queue 事件只在内存提取 `provider`、`auth_index`、时间和 `x-codex-*` 额度响应头。原始 API key、
IP、User-Agent、失败正文、文件名和 queue 原文不会写入 SQLite 或日志。数据库只保存脱敏账号、
Fernet 派生 HMAC、随机公开 ID 和最新额度窗口。

### CPAMP：只读持久化快照

选择 `CPAMP 快照` 后，QuotaHub 只读取该渠道 CPAMP 端点已持久化的数据：

1. `GET /v0/management/auth-files` 获取 Codex 账号清单；
2. 优先按每批最多 200 个账号调用 `POST /v0/management/quota-snapshots/query`；
3. 仅当 query 返回 `404/405` 时，兼容读取
   `GET /v0/management/monitoring/header-snapshots?days=30&limit=5000`；
4. `/auth-files` 暂时不可用时，可用 Header Snapshot 的身份字段构建本轮内存映射。

CPAMP 模式不会调用 `/api-call`，也不会主动请求 ChatGPT。`account_key`、邮箱、文件名和
`auth_index` 只用于单次内存映射，不进入 QuotaHub 数据库、API 或日志。

前端不能自定义上游方法、路径或请求头。

## 采集行为

- OpenCode、Ollama 使用服务级间隔；CPA 账号发现或 CPAMP 快照同步按渠道独立配置。
- 新增、更新凭证或重新启用后会排入后台采集，不提供手动上游刷新接口。
- 普通额度同步与 CPA queue 分别使用 SQLite 租约，多 worker 共享同一 SQLite 时保持单飞。
- CPA queue 每批最多 100 条、单周期最多 10 批；租约丢失后不再发起下一次请求，已经 pop 的批次
  仍会完成安全解析和落库。
- CPAMP query 每批最多 200 个账号；一个批次失败不会清除其他成功批次的额度。
- 失败后等待完整间隔；保留上次成功额度并标记为“缓存已陈旧”。
- 禁用账号或渠道后停止采集、公开页隐藏，但保留快照；删除时级联删除快照。

## 升级到 0.3.2

1. 停止所有旧实例并备份 SQLite。升级迁移期间禁止新旧版本同时运行，并预留至少一个数据库文件
   大小的额外空间；凭证加密迁移会安全重写 SQLite，清除旧页面中的明文残留：

   ```bash
   cp data/quotahub.db "data/quotahub.db.backup-$(date +%Y%m%d-%H%M%S)"
   ```

2. 一次性配置稳定的 `QUOTAHUB_ADMIN_TOKEN` 与 `QUOTAHUB_ENCRYPTION_KEY`。从更早版本升级时，
   旧明文凭证会事务性迁移为 `fernet:v1:` 密文；主密钥错误时应用会拒绝启动。
3. 若需要导入旧 `config.json`，临时设置 `QUOTAHUB_CONFIG=/data/config.json` 或挂载：

   ```yaml
   environment:
     QUOTAHUB_CONFIG: /data/config.json
   volumes:
     - ./data:/data
     - ./config.json:/data/config.json:ro
   ```

4. 先启动单个 0.3.2 实例，确认数据库迁移完成、账号已导入、凭证可解密且可以登录后台。所有旧
   CPA 渠道升级后 queue 默认关闭，历史额度与 `public_id` 保留。
5. 按上文配置 CPA 的 `usage-statistics-enabled` 和 queue retention，确认没有 RESP subscriber、
   其他 HTTP consumer 或旧 QuotaHub 实例，再在管理员页面逐个重新确认独占条件。
6. 为每个 CPA 渠道选择 `仅发现账号`、`原生 HTTP usage` 或 `CPAMP 快照`，验证状态和公开额度后
   再按需扩容。候选版独立 CPAMP 渠道会迁移为单独的统一 CPA 渠道，不自动猜测与现有渠道的归属。
   0.3.1 与 0.3.2 禁止并行运行。
7. 由部署者移除旧 `config.json` 挂载及其中的明文凭证。导入通过 `.imported` 标记保持幂等。

升级前请先备份。Fernet 主密钥错误或旧密文无法解密时，QuotaHub 会拒绝启动，不会静默覆盖数据。

## API 概览

公开只读：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/public/quota` | OpenCode、Ollama 与统一 CPA 渠道的本地额度快照 |
| GET | `/api/public/overview` | 基于快照的概览 |
| GET | `/api/public/analytics/opencode/daily` | SQLite 日统计 |
| GET | `/api/public/analytics/opencode/daily/models` | SQLite 模型日统计 |
| GET | `/api/health` | 健康检查 |

管理员接口统一位于 `/api/admin/*`，包括认证、账号、CPA 渠道与额度来源、使用记录和设置。
所有写请求需要登录会话与 CSRF 校验。旧 `/api/quota`、`/api/ollama/quota` 和分析路径仅保留一版
只读快照兼容入口，并已标记弃用。

## 技术栈

- 后端：Python 3.11+、FastAPI、httpx、SQLite、cryptography/Fernet、uv
- 前端：React 19、TypeScript、Vite、Tailwind CSS
- 部署：Docker 或 uv
