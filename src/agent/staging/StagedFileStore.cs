using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace agent.staging;

/// <summary>
/// v0.17.1 (R335): StagedFileStore — 变更批次持久化 (data/staged/)。落盘但**不占用真实文件地址**:
/// 内容快照存 data/staged/&lt;batch&gt;/&lt;n&gt;.content (原样字节, 非 JSON 转义); 元数据 index.json 原子写
/// (v0.17.0 LockedFileWriter — 双实例并发 stage 安全)。恢复 = 新实例读 index.json → pending 批次仍在
/// (Q3: 用户下次打开 CLI 未审批变更可恢复)。过期三阶段 (Q4): TTL → expired 标记 (内容保留可取回);
/// TTL×2 → reclaimable; 物理删除仅经 ClearExpired(force) 或显式 /cleanup — 不静默丢。
/// 前端 (Q5): 直接读 index.json (含批次元数据+文件清单+staging 内容路径) 或 /staged --json。
/// </summary>
public sealed class StagedFileStore
{
    private readonly string _root;
    private readonly object _lock = new();
    private List<ChangeBatch> _batches = new();

    public string Root => _root;
    public string IndexPath => Path.Combine(_root, "index.json");

    public StagedFileStore(string? dataRoot = null)
    {
        _root = dataRoot is null
            ? Path.Combine(Environment.CurrentDirectory, "data", "staged")
            : Path.Combine(dataRoot, "staged");
        Load();
    }

    public IReadOnlyList<ChangeBatch> All() { lock (_lock) { return _batches.ToList(); } }

    public ChangeBatch? Find(string id) { lock (_lock) { return _batches.FirstOrDefault(b => b.Id == id); } }

    /// <summary>创建批次: 每个 item 的当前目标内容复制入 staging (不写真实文件), 基线哈希记录, index 落盘。</summary>
    public ChangeBatch CreateBatch(string source, IReadOnlyList<(string Path, string NewContent)> changes,
        int ttlDays = 7)
    {
        lock (_lock)
        {
            var batch = new ChangeBatch
            {
                Source = source,
                TtlDays = ttlDays,
                CreatedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                UpdatedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            };
            var dir = Path.Combine(_root, batch.Id);
            Directory.CreateDirectory(dir);
            var idx = 0;
            foreach (var (path, content) in changes)
            {
                var contentFile = Path.Combine(dir, $"{idx}.content");
                // 原样写 staging 内容 (非真实地址)
                using (var fs = new FileStream(contentFile, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    var buf = Encoding.UTF8.GetBytes(content);
                    fs.Write(buf, 0, buf.Length);
                    fs.Flush(true);
                }
                batch.Items.Add(new StagedItem
                {
                    Path = path,
                    BaselineSha = StagingSha.OfFile(path), // 空=目标不存在 (新建语义)
                    ContentFile = contentFile,
                });
                idx++;
            }
            _batches.Add(batch);
            SaveIndex();
            return batch;
        }
    }

    /// <summary>读 item 的 staging 完整内容 (供 /diff、前端取实际落盘内容)。</summary>
    public string ReadItemContent(StagedItem item)
    {
        try { return File.ReadAllText(item.ContentFile); }
        catch { return ""; }
    }

    public void UpdateStatus(string id, string status)
    {
        lock (_lock)
        {
            var b = _batches.FirstOrDefault(x => x.Id == id);
            if (b is null) return;
            b.Status = status;
            b.UpdatedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            SaveIndex();
        }
    }

    /// <summary>物理删除批次 (reject / cleanup)。staging 内容一并删。</summary>
    public void Remove(string id)
    {
        lock (_lock)
        {
            var b = _batches.FirstOrDefault(x => x.Id == id);
            if (b is null) return;
            _batches.Remove(b);
            try
            {
                var dir = Path.Combine(_root, b.Id);
                if (Directory.Exists(dir)) Directory.Delete(dir, recursive: true);
            }
            catch { /* 内容删除失败不阻塞 index 更新 */ }
            SaveIndex();
        }
    }

    /// <summary>过期扫描 (Q4): TTL 到 → expired; TTL×2 到 → reclaimable (可被 cleanup 回收)。</summary>
    public void ScanExpiry(long? nowMs = null)
    {
        lock (_lock)
        {
            var now = nowMs ?? DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            var changed = false;
            foreach (var b in _batches)
            {
                if (!b.IsPending) continue;
                var ageDays = (now - b.CreatedUnixMs) / (double)(24 * 3600 * 1000);
                if (ageDays >= b.TtlDays * 2 && b.Status != "reclaimable")
                {
                    b.Status = "reclaimable"; changed = true;
                }
                else if (ageDays >= b.TtlDays && b.Status == "pending")
                {
                    b.Status = "expired"; changed = true;
                }
            }
            if (changed) SaveIndex();
        }
    }

    /// <summary>强制清理 reclaimable/expired 批次。默认只清 reclaimable (expired 仍可取回)。</summary>
    public int Cleanup(bool includeExpired = false)
    {
        lock (_lock)
        {
            var targets = _batches.Where(b => b.Status == "reclaimable"
                || (includeExpired && b.Status == "expired")).Select(b => b.Id).ToList();
            foreach (var id in targets)
            {
                var b = _batches.FirstOrDefault(x => x.Id == id);
                if (b is null) continue;
                _batches.Remove(b);
                try { var dir = Path.Combine(_root, b.Id); if (Directory.Exists(dir)) Directory.Delete(dir, true); }
                catch { }
            }
            if (targets.Count > 0) SaveIndex();
            return targets.Count;
        }
    }

    // ---- 持久化 ----
    private void Load()
    {
        try
        {
            if (!File.Exists(IndexPath)) return;
            var json = File.ReadAllText(IndexPath);
            using var doc = System.Text.Json.JsonDocument.Parse(json);
            if (!doc.RootElement.TryGetProperty("batches", out var arr)) return;
            foreach (var el in arr.EnumerateArray())
            {
                var b = new ChangeBatch
                {
                    Id = el.GetProperty("id").GetString() ?? "",
                    Source = el.TryGetProperty("source", out var s) ? s.GetString() ?? "agent" : "agent",
                    Status = el.GetProperty("status").GetString() ?? "pending",
                    CreatedUnixMs = el.GetProperty("created").GetInt64(),
                    UpdatedUnixMs = el.GetProperty("updated").GetInt64(),
                    TtlDays = el.TryGetProperty("ttl_days", out var t) ? t.GetInt32() : 7,
                };
                if (el.TryGetProperty("items", out var items))
                {
                    foreach (var it in items.EnumerateArray())
                    {
                        b.Items.Add(new StagedItem
                        {
                            Path = it.GetProperty("path").GetString() ?? "",
                            BaselineSha = it.GetProperty("base").GetString() ?? "",
                            ContentFile = it.GetProperty("content").GetString() ?? "",
                            Applied = it.TryGetProperty("applied", out var ap) && ap.GetBoolean(),
                        });
                    }
                }
                if (b.Id.Length > 0) _batches.Add(b);
            }
        }
        catch { /* 损坏容忍 — staging 元数据坏不致命 */ }
    }

    private void SaveIndex()
    {
        try
        {
            Directory.CreateDirectory(_root);
            var sb = new StringBuilder();
            sb.Append("{\"batches\":[");
            var first = true;
            foreach (var b in _batches.OrderBy(x => x.CreatedUnixMs))
            {
                if (!first) sb.Append(',');
                first = false;
                sb.Append("{\"id\":").Append(Esc(b.Id))
                  .Append(",\"source\":").Append(Esc(b.Source))
                  .Append(",\"status\":").Append(Esc(b.Status))
                  .Append(",\"created\":").Append(b.CreatedUnixMs)
                  .Append(",\"updated\":").Append(b.UpdatedUnixMs)
                  .Append(",\"ttl_days\":").Append(b.TtlDays)
                  .Append(",\"items\":[");
                var f2 = true;
                foreach (var it in b.Items)
                {
                    if (!f2) sb.Append(',');
                    f2 = false;
                    sb.Append("{\"path\":").Append(Esc(it.Path))
                      .Append(",\"base\":").Append(Esc(it.BaselineSha))
                      .Append(",\"content\":").Append(Esc(it.ContentFile))
                      .Append(",\"applied\":").Append(it.Applied ? "true" : "false")
                      .Append('}');
                }
                sb.Append("]}");
            }
            sb.Append("]}");
            agent.execution.AtomicFileWriter.WriteAllText(IndexPath, sb.ToString());
        }
        catch { /* index 写失败不致命 — 下次 Save 重试 */ }
    }

    private static string Esc(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        sb.Append('"');
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4"));
                    else sb.Append(c);
                    break;
            }
        }
        sb.Append('"');
        return sb.ToString();
    }
}
