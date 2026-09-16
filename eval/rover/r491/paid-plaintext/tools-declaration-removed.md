# B 臂每次请求**附带**、T 臂**去掉**的工具声明正文（从源码常量机取）

| 名称 | 描述 | parameters(JSON) |
|---|---|---|
| `ListDir` | 列出工作区目录条目(相对路径/大小/类型) | `{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的目录路径, 省略=根"}},"required":[]}` |
| `ReadFile` | 读取工作区文本文件 | `{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"max_bytes":{"type":"integer","description":"最大字节数(默认8192)"}},"required":["path"]}` |
| `WriteFile` | 写入/覆盖工作区文本文件 | `{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"content":{"type":"string","description":"文件内容"}},"required":["path","content"]}` |
| `RunCommand` | 在工作区根执行一条命令并返回 stdout/stderr/退出码 | `{"type":"object","properties":{"command":{"type":"string","description":"命令原文"},"timeout_ms":{"type":"integer","description":"超时毫秒(默认120000, 上限600000)"}},"required":["command"]}` |

- Chat 线格式字符数 = **1020**；Responses 平铺版 = **968**

```json
[{"type":"function","function":{"name":"ListDir","description":"列出工作区目录条目(相对路径/大小/类型)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的目录路径, 省略=根"}},"required":[]}}},
{"type":"function","function":{"name":"ReadFile","description":"读取工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"max_bytes":{"type":"integer","description":"最大字节数(默认8192)"}},"required":["path"]}}},
{"type":"function","function":{"name":"WriteFile","description":"写入/覆盖工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"content":{"type":"string","description":"文件内容"}},"required":["path","content"]}}},
{"type":"function","function":{"name":"RunCommand","description":"在工作区根执行一条命令并返回 stdout/stderr/退出码","parameters":{"type":"object","properties":{"command":{"type":"string","description":"命令原文"},"timeout_ms":{"type":"integer","description":"超时毫秒(默认120000, 上限600000)"}},"required":["command"]}}}]
```
