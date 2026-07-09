# QuotaHub

由于 OpenCode Go 和 Ollama 多账号使用时查看额度不太方便，Vibe了一个小工具从各平台 Dashboard 抓取并展示账号额度。


## 致谢

感谢 [LinuxDo](https://linux.do) 社区佬友们的交流与分享；

OpenCode Go 额度查询功能的实现参考了 [opencode-cc](https://github.com/Kiowx/opencode-cc)（[@Kiowx](https://github.com/Kiowx)）。


## Docker 部署

```bash
cp config.json.example config.json
cp docker-compose.yml.example docker-compose.yml
docker compose up -d --build --force-recreate
```

浏览器打开 http://localhost:28787 （端口由 `QUOTAHUB_LISTEN_PORT` 决定）

SQLite 数据库在 `/data/quotahub.db`，初版升级用户可将`config.json` 挂载到 `/data/config.json`以进行数据迁移。

## 配置说明

| 字段 | 说明 |
|------|------|
| `listen_host` / `listen_port` | 监听地址 |
| `refresh.*` | 额度自动刷新间隔 |
| `usage_sync.*` | 使用记录自动增量同步 |
| `opencode.usage_server_id` | OpenCode getUsageInfo 端点 ID（一般无需修改） |
| `import_accounts` | **仅首次启动**导入到 SQLite，之后请在页面管理账号 |

初版更新后会自动导入配置信息，完成后写入 `/data/.imported`，不再读取 config 中的账号字段，可安全删除config文件。


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

完整 UI：仪表盘、账号管理、账户详情（额度 + 使用记录）、设置。


## 技术栈

- 后端：Python 3.13、FastAPI、httpx、SQLite、uv
- 前端：Vite、React、react-router-dom、Tailwind CSS
- 部署：Docker multi-stage
