# FrontendApi v1 对接 DEMO (WinForms)

`samples/FrontendApi.WinForms` — 用 WinForms 对接 `agent.frontendapi` 的最小可运行前端示例，
用于验证「外部 IDE/前端只对接统一接口」这一契约，并通过原始协议日志排查 agent 内部问题。

> ⚠ **目标框架 `net10.0-windows`**：仅 Windows 可构建运行。
> 刻意**未加入 `agent.sln`** — 仓库 CI 跑 `ubuntu-latest` 且 `dotnet build -warnaserror`，
> 若进 sln 会因 Linux 无 WindowsDesktop 引用包而构建失败。**此项目不参与 CI 构建。**

## 1. 启动 agent 侧

```bash
cd src/agent.host
dotnet run -- --frontend-api 47810
```

控制台会打印（`--frontend-api` 模式日志中的关键两行）：

```
frontend-api: READY :47810 (chat.send 直通 V2 管线; Ctrl+C 退出)
frontend-api: AUTH token = <hex 或 env 注入值> (客户端首行 {"type":"auth","token":"..."} ...)
```

- **固定 token（推荐）**：启动前 `export AGENTFRAMEWORK_FRONTEND_TOKEN=mytoken`，DEMO 填 `mytoken`。
- **关闭鉴权（仅本机调试）**：`export AGENTFRAMEWORK_FRONTEND_AUTH=0`，DEMO 的 Token 留空。

## 2. 构建运行 DEMO（Windows）

```powershell
cd samples\FrontendApi.WinForms
dotnet run
```

## 3. 界面与已实现 api

| 区域 | api | 说明 |
|---|---|---|
| Chat | `chat.send` | payload `{"text":"..."}` → `{"reply":"...","success":bool}`，直通 V2 完整管线 |
| 状态 | `state.snapshot` | 真实快照（session_id / model{id,provider,selection,mode,switches} / uptime_ms / ready） |
| 状态 | `state.hello` | `{"hello":true}` |
| 元域 | `meta.info` | 版本 + `contract` + `domains` |
| 元域 | `meta.ping` | `{"pong":true}` |

底部「协议日志」实时打印 `>>` 发送 / `<<` 接收的原始 JSON Lines，是排查问题的主手段。

## 4. 协议要点（实测自服务端）

```jsonc
// 鉴权（首行，仅 auth 开启时）: 成功无任何响应；失败 → 服务端静默断连（防枚举）
{"type":"auth","token":"..."}

// 请求
{"v":1,"type":"req","req_id":"r1","api":"chat.send","payload":{"text":"你好"}}

// 响应
{"v":1,"type":"resp","req_id":"r1","ok":true,"payload":{"reply":"...","success":true}}

// 失败
{"v":1,"type":"resp","req_id":"r1","ok":false,"payload":{},"error":{"code":"bad_payload","msg":"..."}}

// 事件（单向推送，无 req_id）
{"v":1,"type":"event","event":"...","payload":{...}}
```

错误码：`unknown_api` / `bad_payload` / `busy` / `conflict` / `not_found` / `internal`。

## 5. 已知服务端行为（DEMO 已针对性提示）

1. **鉴权失败 = 静默断连**，无任何响应 → DEMO 在请求失败时提示「疑似 token 错误」。
2. **全局限流 10 req/s、桶容量 20、并发上限 4**（`FrontendAccessControl`）→ 超限回 `error.code="busy"`。
   `chat.send` 单次耗时较长，连续发送容易触发并发上限。
3. **旧实现限流响应 `req_id` 恒为 `"rate"`**，客户端无法按 req_id 关联（服务端 v0.21.1 已修复为回显真实 req_id；
   DEMO 仍保留「退化为完成最早未决请求」的兼容逻辑，避免在旧服务端上永久挂起）。

## 6. 本 DEMO 暴露的 agent 内部问题（已在 v0.21.1 修复 / 记录）

详见 `docs/improvements.md` R367：

- 限流响应 `req_id` 硬编码 `"rate"`，违反「响应回显 req_id」契约 → 已回显真实 req_id。
- `chat.send` 缺 `text` 抛 `BadPayloadException`，被服务端统一 catch 成 `internal` → 已映射为 `bad_payload`。
- 请求行无长度上限，客户端发送不带 `\n` 的超长数据可致 `pending` 无界增长 → 已加上限并断连。
- `meta.info` 版本硬编码 0.20.5（实际 v0.21.0）→ 已校正。
