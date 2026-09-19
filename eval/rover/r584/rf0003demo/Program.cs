using System.Text;
using agent.files;

// R584 真机 E2E: 走插件注册表取服务 -> 真实文件系统上跑 竞争/合并/备份/还原 四条路径。
var root = Path.Combine(Path.GetTempPath(), "rf0003demo-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);

var registry = new FileServicePluginRegistry(new IFileServicePlugin[] { new NativeFileServicePlugin() });
var plugin = registry.FirstAvailable();
Console.WriteLine($"[0] 插件: {plugin?.Name ?? "<无>"} available={plugin?.IsAvailable}");
var svc = plugin!.Create(new FileServiceOptions { WorkspaceRoot = root });

void Dump(string label) => Console.WriteLine($"[{label}] 盘上 sha={Sha(Path.Combine(root, "a.txt"))} 文本={Escape(File.ReadAllText(Path.Combine(root, "a.txt")))}");

File.WriteAllText(Path.Combine(root, "a.txt"), "1 alpha\n2 beta\n3 gamma\n", new UTF8Encoding(false));
Dump("1 初始");

var read = await svc.SnapshotAsync("a.txt");
Console.WriteLine($"[2] agent 读: sha={read.Sha256[..16]} bytes={read.Bytes}");

// 用户在同一文件上改了第 2 行（外部写盘）—— 与 agent 的改动重叠
File.WriteAllText(Path.Combine(root, "a.txt"), "1 alpha\n2 USER\n3 gamma\n", new UTF8Encoding(false));
var userSha = Sha(Path.Combine(root, "a.txt"));
Console.WriteLine($"[3] 用户改第2行: sha={userSha[..16]}");

var overlap = await svc.ApplyAsync(new FileEditRequest
{
    Path = "a.txt",
    ExpectedSha256 = read.Sha256,
    BaseText = "1 alpha\n2 beta\n3 gamma\n",
    NewText = "1 alpha\n2 AGENT\n3 gamma\n",
    Source = "demo-overlap",
});
Console.WriteLine($"[4] agent 提交(重叠): outcome={overlap.Outcome} 冲突={overlap.Conflicts.Count} 盘上 sha 未变={Sha(Path.Combine(root, "a.txt")) == userSha} 备份={overlap.BackupPath ?? "<无>"}");
foreach (var c in overlap.Conflicts)
{
    Console.WriteLine($"    冲突块 base[{c.BaseStartLine}..{c.BaseStartLine + c.BaseLineCount}) ours={Escape(c.OursText)} theirs={Escape(c.TheirsText)}");
}

// 非重叠: 用户改第 1 行 + 末尾追加, agent 改第 3 行 ⇒ 应自动合并
var snap2 = await svc.SnapshotAsync("a.txt");
File.WriteAllText(Path.Combine(root, "a.txt"), "1 USERX\n2 USER\n3 gamma\n4 appended\n", new UTF8Encoding(false));
var merged = await svc.ApplyAsync(new FileEditRequest
{
    Path = "a.txt",
    ExpectedSha256 = snap2.Sha256,
    BaseText = "1 alpha\n2 USER\n3 gamma\n",
    NewText = "1 alpha\n2 USER\n3 AGENT\n",
    Source = "demo-merge",
});
Console.WriteLine($"[5] agent 提交(非重叠): outcome={merged.Outcome} 盘上={Escape(File.ReadAllText(Path.Combine(root, "a.txt")))}");
Console.WriteLine($"    merged 文本回执={Escape(merged.MergedText ?? "<null>")}");

// 备份链 + 还原
var backups = svc.ListBackups("a.txt");
Console.WriteLine($"[6] 备份链 {backups.Count} 条:");
foreach (var b in backups)
{
    Console.WriteLine($"    sha={b.Sha256[..16]} bytes={b.Bytes} source={b.Source} blob={Path.GetFileName(b.BlobPath)}");
}

var oldest = backups[0];
var blobText = File.ReadAllText(oldest.BlobPath);
var restore = svc.Restore(oldest);
var restored = File.ReadAllText(Path.Combine(root, "a.txt"));
Console.WriteLine($"[7] 还原最早备份: outcome={restore.Outcome} 还原前盘上={Escape(blobText)} 逐位等于备份内容={restored == blobText} 还原后备份链={svc.ListBackups("a.txt").Count} 条");

// 负控: 越界路径必拒
var escape = await svc.ApplyAsync(new FileEditRequest { Path = "../escape.txt", ExpectedSha256 = string.Empty, NewText = "x", Source = "demo-escape" });
Console.WriteLine($"[8] 负控 越界路径: outcome={escape.Outcome} note={escape.Note}");
Console.WriteLine($"[9] 备份库根: {Path.GetFileName(((LocalFileService)svc).Backups.Root)} 索引行数={File.ReadAllLines(((LocalFileService)svc).Backups.IndexPath).Length}");
Console.WriteLine($"DEMO_DONE root={root}");

static string Sha(string path) => ContentHash.OfBytes(File.ReadAllBytes(path))[..16];
static string Escape(string text) => "\"" + text.Replace("\n", "\\n") + "\"";
