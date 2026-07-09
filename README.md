# QuotaHub

由于 OpenCode Go 和 Ollama 多账号使用时查看额度不太方便，Vibe了一个小工具从各平台 Dashboard 抓取并展示账号额度。


## 致谢

感谢 [LinuxDo](https://linux.do) 社区佬友们的交流与分享；

OpenCode Go 额度查询功能的实现参考了 [opencode-cc](https://github.com/Kiowx/opencode-cc)（[@Kiowx](https://github.com/Kiowx)）。


## Docker 部署

```bash
cp docker-compose.yml.example docker-compose.yml
docker compose up -d --build --force-recreate
```

浏览器打开 http://localhost:28787 （端口由 `QUOTAHUB_LISTEN_PORT` 决定）

数据目录默认为 `./data`，内含 SQLite 数据库 `quotahub.db` 与服务设置。


### 从 v0.1 升级

首次升级可**临时**挂载旧 `config.json`，自动导入账号与设置后写入数据库：

```yaml
environment:
  QUOTAHUB_CONFIG: /data/config.json
volumes:
  - ./data:/data
  - ./config.json:/data/config.json:ro
```

若曾在设置页保存过配置，同目录下的 `service.json` 也会一并迁移（`service.json` 优先级更高）。

导入完成后可去掉 `config.json` 挂载；账号与设置在 SQLite 中维护，不再依赖配置文件。


## 配置说明

运行时**不再依赖** `config.json`，配置在「设置」页面修改，后续变更将保存到 SQLite。

| 来源 | 说明 |
|------|------|
| 环境变量 `QUOTAHUB_LISTEN_HOST` / `QUOTAHUB_LISTEN_PORT` | 监听地址（优先） |
| 环境变量 `QUOTAHUB_DATA` | 数据目录，默认 `/data` |
| SQLite `service_settings` | 刷新间隔、同步参数等 |
| `config.json`（可选，仅迁移用） | 首次导入账号与旧版设置 |

`import_accounts` 块或顶层账号字段仅在首次导入时读取，完成后写入 `/data/.imported`。


## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/quota` | 所有 OpenCode 账号额度 |
| GET | `/api/ollama/quota` | 所有 Ollama 账号额度 |
| GET/POST | `/api/accounts/opencode` | OpenCode 账号列表 / 新增 |
| PUT/DELETE | `/api/accounts/opencode/{id}` | 更新 / 删除 |
| GET | `/api/accounts/opencode/{id}/usage` | 读本地使用记录 |
| POST | `/api/accounts/opencode/{id}/usage/sync` | 增量同步 |
| POST | `/api/accounts/opencode/{id}/usage/backfill` | 补拉历史 |
| GET/POST | `/api/accounts/ollama` | Ollama 账号 CRUD |
| GET/PUT | `/api/config` | 读取 / 更新服务设置 |

完整 UI：数据概览、账号额度、调用日志、账号管理、设置。


## 技术栈

- 后端：Python 3.13、FastAPI、httpx、SQLite、uv
- 前端：Vite、React、react-router-dom、Tailwind CSS
- 部署：Docker multi-stage
