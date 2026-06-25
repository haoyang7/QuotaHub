# QuotaHub

由于 OpenCode Go 和 Ollama 多账号使用时查看额度不太方便，Vibe了一个小工具从各平台 Dashboard 抓取并展示账号额度。


## 致谢

感谢 [LinuxDo](https://linux.do) 社区佬友们的交流与分享；

OpenCode Go 额度查询功能的实现参考了 [opencode-cc](https://github.com/Kiowx/opencode-cc)（[@Kiowx](https://github.com/Kiowx)），感谢佬友的开源分享。


## Docker部署

```bash
cp config.json.example config.json
cp docker-compose.yml.example docker-compose.yml
# 编辑 config.json，填入 auth_cookie
# 需要出站代理时，在 docker-compose.yml 中设置 HTTP_PROXY / HTTPS_PROXY

docker compose up -d --build --force-recreate
```

浏览器打开 http://localhost:28787 （端口由 `QUOTAHUB_LISTEN_PORT` 或 `config.json` 的 `listen_port` 决定）

更新镜像：

```bash
docker compose up -d --build --force-recreate
```

`config.json` 通过 volume 挂载到容器 `/data/config.json`，改配置后重建容器生效：

```bash
docker compose up -d --force-recreate
```

## config.json 字段

| 字段 | 说明 |
|------|------|
| `listen_host` / `listen_port` | 本地运行时监听地址；Docker 下可由 `QUOTAHUB_LISTEN_HOST` / `QUOTAHUB_LISTEN_PORT` 覆盖 |
| `refresh.ollama.auto_refresh` | Ollama 是否自动刷新（默认 `true`） |
| `refresh.ollama.interval_sec` | Ollama 自动刷新间隔秒数（默认 `300`，最小 `15`） |
| `refresh.opencode_go.auto_refresh` | OpenCode Go 是否自动刷新（默认 `true`） |
| `refresh.opencode_go.interval_sec` | OpenCode Go 自动刷新间隔秒数（默认 `60`，最小 `15`） |
| `ollama_accounts[].name` | Ollama 展示名称 |
| `ollama_accounts[].session_cookie` | 登录 Cookie（`aid=...; __Secure-session=...`） |
| `ollama_accounts[].show_session` | 是否显示 Session 额度 |
| `ollama_accounts[].show_weekly` | 是否显示周额度 |
| `opencode_accounts[].name` | 展示名称 |
| `opencode_accounts[].workspace_id` | 工作区 ID 或名称 |
| `opencode_accounts[].auth_cookie` | 登录 Cookie（`auth=...`） |
| `opencode_accounts[].show_rolling` | 是否显示 5h 滚动额度 |
| `opencode_accounts[].show_weekly` | 是否显示周额度 |
| `opencode_accounts[].show_monthly` | 是否显示月额度 |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/quota` | 查询 OpenCode Go 额度 |
| GET | `/api/ollama/quota` | 查询 Ollama Cloud 额度 |
| GET | `/api/config` | 配置状态（Cookie 掩码） |

## 技术栈

- 后端：Python 3.13、FastAPI、httpx、uv（托管 `frontend/dist`）
- 前端：Vite、React、TypeScript、Tailwind CSS、shadcn/ui 风格组件、pnpm
- 部署：Docker multi-stage 构建
