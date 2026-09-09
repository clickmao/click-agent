using System;
using System.IO;
using System.Linq;
using Xunit;
using agent.staging;

namespace agentframework.tests;

/// <summary>v0.17.1 (R335): 离线变更 staging + 用户审批 — 批次落盘不占真实地址 / 恢复 / 过期 /
/// apply 基线比对 (VS Code 编辑场景防覆盖) / 多批合并 / reject / JSON 输出。</summary>
public class StagedApprovalTests
{
    private static string TempDir()
    {
        var d = Path.Combine(Path.GetTempPath(), "af-staging-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(d);
        return d;
    }

    private static string MakeTarget(string dir, string name, string content)
    {
        var p = Path.Combine(dir, name);
        File.WriteAllText(p, content);
        return p;
    }

    [Fact]
    public void CreateBatch_ContentInStaging_NotRealPath()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "real.txt", "original");
        var store = new StagedFileStore(dataRoot);
        var batch = store.CreateBatch("test", new[] { (target, "NEW CONTENT") });
        Assert.Equal("pending", batch.Status);
        Assert.Equal("original", File.ReadAllText(target)); // 真实文件零变化 (未占用地址)
        var contentFile = batch.Items[0].ContentFile;
        Assert.StartsWith(Path.Combine(dataRoot, "staged", batch.Id), contentFile);
        Assert.Equal("NEW CONTENT", File.ReadAllText(contentFile)); // staging 有完整新内容
        Assert.Equal(StagingSha.OfFile(target), batch.Items[0].BaselineSha);
    }

    [Fact]
    public void Recovery_NewStoreInstance_SeesPendingBatch()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "a.txt", "v1");
        var s1 = new StagedFileStore(dataRoot);
        var b = s1.CreateBatch("gen", new[] { (target, "v2-from-agent") });
        var s2 = new StagedFileStore(dataRoot); // 模拟下次打开 CLI — 恢复
        var restored = s2.Find(b.Id);
        Assert.NotNull(restored);
        Assert.Equal("pending", restored!.Status);
        Assert.Equal("v2-from-agent", s2.ReadItemContent(restored.Items[0]));
    }

    [Fact]
    public void Apply_UserUntouched_Succeeds_WritesRealFile()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "b.txt", "original");
        var store = new StagedFileStore(dataRoot);
        var b = store.CreateBatch("gen", new[] { (target, "approved-content") });
        var ctl = new ApprovalController(store);
        var r = ctl.Apply(b.Id);
        Assert.True(r.FullyApplied);
        Assert.Equal("approved-content", File.ReadAllText(target));
        Assert.Equal("approved", store.Find(b.Id)!.Status);
    }

    [Fact]
    public void Apply_UserEditedSinceBatch_ConflictRefused_NoOverwrite()
    {
        // Q1 核心: VS Code 用户正在编辑同文件 → 批次创建后被外部改 → 应用拒绝覆盖
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "c.txt", "original");
        var store = new StagedFileStore(dataRoot);
        var b = store.CreateBatch("gen", new[] { (target, "agent-wants-this") });
        File.WriteAllText(target, "USER EDITED IN VSCODE"); // 模拟用户/编辑器修改
        var ctl = new ApprovalController(store);
        var r = ctl.Apply(b.Id);
        Assert.Equal(0, r.AppliedCount);
        Assert.Equal(1, r.ConflictCount);
        Assert.Equal("USER EDITED IN VSCODE", File.ReadAllText(target)); // 未覆盖!
        Assert.Equal("rejected", store.Find(b.Id)!.Status); // 无一项成功 → rejected
    }

    [Fact]
    public void Apply_NewFileSemantics_Works()
    {
        var dataRoot = TempDir();
        var target = Path.Combine(dataRoot, "newfile.txt"); // 不存在
        var store = new StagedFileStore(dataRoot);
        var b = store.CreateBatch("gen", new[] { (target, "brand-new") });
        Assert.Equal("", b.Items[0].BaselineSha); // 新建: 空基线
        var ctl = new ApprovalController(store);
        var r = ctl.Apply(b.Id);
        Assert.True(r.FullyApplied);
        Assert.Equal("brand-new", File.ReadAllText(target));
    }

    [Fact]
    public void MultiBatch_ApproveAll_AppliesInOrder_ThenConflict()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "m.txt", "v0");
        var store = new StagedFileStore(dataRoot);
        var bA = store.CreateBatch("gen-A", new[] { (target, "A-content") });
        var bB = store.CreateBatch("gen-B", new[] { (target, "B-content") }); // 基线仍是 v0 (A 未应用)
        var ctl = new ApprovalController(store);
        var rA = ctl.Apply(bA.Id);
        Assert.True(rA.FullyApplied);
        var rB = ctl.Apply(bB.Id); // A 已应用 → B 基线过期 → 冲突
        Assert.Equal(0, rB.AppliedCount);
        Assert.Equal(1, rB.ConflictCount);
        Assert.Equal("A-content", File.ReadAllText(target)); // B 未覆盖 A
        Assert.Equal("rejected", store.Find(bB.Id)!.Status);
    }

    [Fact]
    public void Expiry_ThreeStage_NoSilentDelete()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "e.txt", "orig");
        var store = new StagedFileStore(dataRoot);
        var b = store.CreateBatch("gen", new[] { (target, "new") }, ttlDays: 1);
        // 制造时钟: 用真实 TTL=1 天不可测 — 手动改批次时间后 ScanExpiry
        b.CreatedUnixMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - (25 * 3600 * 1000L); // 25h = >1d
        b.UpdatedUnixMs = b.CreatedUnixMs;
        store.UpdateStatus(b.Id, "pending"); // 触发保存 (已改时间)
        // 直接构造过期扫描 (真实 store 时间基于 now — 批次已改旧 → 过期)
        store.ScanExpiry();
        var afterExpire = store.Find(b.Id);
        Assert.Equal("expired", afterExpire!.Status); // TTL 到 → expired (内容保留)
        Assert.True(File.Exists(afterExpire.Items[0].ContentFile), "expired 内容文件应保留可取回");
        // reclaimable 清理:
        store.UpdateStatus(b.Id, "reclaimable");
        var removed = store.Cleanup();
        Assert.Equal(1, removed);
        Assert.Null(store.Find(b.Id));
    }

    [Fact]
    public void Reject_RemovesBatchAndContent()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "r.txt", "orig");
        var store = new StagedFileStore(dataRoot);
        var b = store.CreateBatch("gen", new[] { (target, "junk") });
        var contentFile = b.Items[0].ContentFile;
        store.Remove(b.Id);
        Assert.Null(store.Find(b.Id));
        Assert.False(File.Exists(contentFile));
        Assert.Equal("orig", File.ReadAllText(target));
    }

    [Fact]
    public void ListJson_OutputParsable()
    {
        var dataRoot = TempDir();
        var target = MakeTarget(dataRoot, "j.txt", "v");
        var store = new StagedFileStore(dataRoot);
        store.CreateBatch("gen", new[] { (target, "json-content") });
        var ctl = new ApprovalController(store);
        var json = ctl.ListPending("--json");
        using var doc = System.Text.Json.JsonDocument.Parse(json);
        Assert.True(doc.RootElement.TryGetProperty("batches", out var arr));
        Assert.True(arr.GetArrayLength() >= 1);
        var first = arr.EnumerateArray().First();
        Assert.Equal("pending", first.GetProperty("status").GetString());
        var items = first.GetProperty("items");
        Assert.True(File.Exists(items[0].GetProperty("content_file").GetString()));
    }

    [Fact]
    public void CorruptIndex_Tolerated_NoThrow()
    {
        var dataRoot = TempDir();
        Directory.CreateDirectory(Path.Combine(dataRoot, "staged"));
        File.WriteAllText(Path.Combine(dataRoot, "staged", "index.json"), "{corrupt");
        var store = new StagedFileStore(dataRoot); // 不抛
        Assert.Empty(store.All());
        store.CreateBatch("x", new[] { (Path.Combine(dataRoot, "f.txt"), "ok") });
        Assert.Single(store.All());
    }
}
