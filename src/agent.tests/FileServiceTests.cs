using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using agent.files;
using Xunit;

namespace agent.tests;

/// <summary>
/// R584 文件插件服务单测（RF0003）。断言面: ① 写盘前必备份且备份内容 == 前态字节; ② 备份失败/非文本/
/// 越界/超合并上限 ⇒ 拒写且盘上逐位不变（fail-closed）; ③ 现盘被外部改动 ⇒ 非重叠自动合并、重叠冲突不写;
/// ④ 还原逐位可逆且还原本身也先备份; ⑤ 内容寻址去重 + 保留策略; ⑥ 插件注册表无可用插件即诚实不可用。
/// </summary>
public sealed class FileServiceTests
{
    private static string NewRoot()
    {
        var root = Path.Combine(Path.GetTempPath(), "rf0003-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        return root;
    }

    private static LocalFileService NewService(string root, Action<FileServiceOptions>? tweak = null)
    {
        var options = new FileServiceOptions { WorkspaceRoot = root };
        tweak?.Invoke(options);
        return new LocalFileService(options);
    }

    private static void Write(string root, string name, string text)
        => File.WriteAllBytes(Path.Combine(root, name), new UTF8Encoding(false).GetBytes(text));

    private static string Read(string root, string name)
        => File.ReadAllText(Path.Combine(root, name));

    [Fact]
    public async Task Apply_FastPath_WritesAndBacksUpPreviousBytes()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "l1\nl2\n");
        var before = await svc.SnapshotAsync("a.txt");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            NewText = "l1\nl2\nl3\n",
            Source = "t1",
        });

        Assert.Equal(FileEditOutcome.Applied, result.Outcome);
        Assert.Equal("l1\nl2\nl3\n", Read(root, "a.txt"));
        var backups = svc.ListBackups("a.txt");
        Assert.Single(backups);
        Assert.Equal(before.Sha256, backups[0].Sha256);
        Assert.Equal("l1\nl2\n", File.ReadAllText(backups[0].BlobPath));
    }

    [Fact]
    public async Task Apply_BackupFailure_RejectsAndLeavesFileUntouched()
    {
        var root = NewRoot();
        Write(root, "blocker", "not-a-directory");
        var svc = NewService(root, o => o.BackupRoot = Path.Combine(root, "blocker", "sub"));
        Write(root, "a.txt", "keep-me\n");
        var before = await svc.SnapshotAsync("a.txt");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            NewText = "changed\n",
            Source = "t2",
        });

        Assert.Equal(FileEditOutcome.Rejected, result.Outcome);
        Assert.Contains("备份失败", result.Note);
        Assert.Equal("keep-me\n", Read(root, "a.txt"));
    }

    [Fact]
    public async Task Apply_OverlappingExternalChange_ConflictsAndLeavesDiskUntouched()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "a\nb\nc\n");
        var before = await svc.SnapshotAsync("a.txt");
        Write(root, "a.txt", "a\nX\nc\n");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            BaseText = "a\nb\nc\n",
            NewText = "a\nY\nc\n",
            Source = "t3",
        });

        Assert.Equal(FileEditOutcome.Conflict, result.Outcome);
        Assert.Equal("a\nX\nc\n", Read(root, "a.txt"));
        Assert.Single(result.Conflicts);
        Assert.Equal("X", result.Conflicts[0].OursText);
        Assert.Equal("Y", result.Conflicts[0].TheirsText);
        Assert.Equal(1, result.Conflicts[0].BaseStartLine);
        Assert.Contains("<<<<<<<", result.MergedText);
        Assert.Empty(svc.ListBackups("a.txt"));
    }

    [Fact]
    public async Task Apply_NonOverlappingExternalChange_AutoMergesBothSides()
    {
        var root = NewRoot();
        var svc = NewService(root);
        const string Base = "a\nb\nc\nd\ne\n";
        Write(root, "a.txt", Base);
        var before = await svc.SnapshotAsync("a.txt");
        const string User = "a\nB\nc\nd\ne\nf\n";
        Write(root, "a.txt", User);

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            BaseText = Base,
            NewText = "a\nb\nc\nd\nE\n",
            Source = "t4",
        });

        Assert.Equal(FileEditOutcome.MergedAuto, result.Outcome);
        Assert.Equal("a\nB\nc\nd\nE\nf\n", Read(root, "a.txt"));
        var backups = svc.ListBackups("a.txt");
        Assert.Single(backups);
        Assert.Equal(ContentHash.OfText(User), backups[0].Sha256);
    }

    [Fact]
    public async Task Apply_StaleExpectedSha_WithoutBase_ReturnsStaleBase()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "v1\n");
        var before = await svc.SnapshotAsync("a.txt");
        Write(root, "a.txt", "v2-by-user\n");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            NewText = "v3-by-agent\n",
            Source = "t5",
        });

        Assert.Equal(FileEditOutcome.StaleBase, result.Outcome);
        Assert.Equal("v2-by-user\n", Read(root, "a.txt"));
    }

    [Fact]
    public async Task Apply_DeleteRace_ExpectedShaButFileGone_ReturnsStaleBase()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "v1\n");
        var before = await svc.SnapshotAsync("a.txt");
        File.Delete(Path.Combine(root, "a.txt"));

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            BaseText = "v1\n",
            NewText = "v2\n",
            Source = "t6",
        });

        Assert.Equal(FileEditOutcome.StaleBase, result.Outcome);
        Assert.False(File.Exists(Path.Combine(root, "a.txt")));
    }

    [Fact]
    public async Task Apply_MergeDisabled_ExternalChangeIsRefused()
    {
        var root = NewRoot();
        var svc = NewService(root, o => o.AllowMerge = false);
        Write(root, "a.txt", "a\nb\n");
        var before = await svc.SnapshotAsync("a.txt");
        Write(root, "a.txt", "a\nB\n");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            BaseText = "a\nb\n",
            NewText = "a\nb\nc\n",
            Source = "t7",
        });

        Assert.Equal(FileEditOutcome.StaleBase, result.Outcome);
        Assert.Equal("a\nB\n", Read(root, "a.txt"));
    }

    [Fact]
    public async Task Apply_NonTextFile_IsRejected()
    {
        var root = NewRoot();
        var svc = NewService(root);
        var raw = new byte[] { 0xFF, 0xFE, 0x00, 0x41, 0xC3 };
        File.WriteAllBytes(Path.Combine(root, "bin.dat"), raw);

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "bin.dat",
            NewText = "text\n",
            Source = "t8",
        });

        Assert.Equal(FileEditOutcome.Rejected, result.Outcome);
        Assert.Equal(raw, File.ReadAllBytes(Path.Combine(root, "bin.dat")));
    }

    [Fact]
    public async Task Apply_PathEscape_IsRejected()
    {
        var root = NewRoot();
        var svc = NewService(root);
        var outside = Path.Combine(Path.GetDirectoryName(root)!, "rf0003-outside-" + Guid.NewGuid().ToString("N") + ".txt");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = outside,
            NewText = "x\n",
            Source = "t9",
        });

        Assert.Equal(FileEditOutcome.Rejected, result.Outcome);
        Assert.Contains("越界", result.Note);
        Assert.False(File.Exists(outside));
    }

    [Fact]
    public async Task Apply_NewFile_CreatesWithoutBackup()
    {
        var root = NewRoot();
        var svc = NewService(root);

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "nested/new.txt",
            NewText = "hello\n",
            Source = "t10",
        });

        Assert.Equal(FileEditOutcome.Applied, result.Outcome);
        Assert.Equal("hello\n", Read(root, Path.Combine("nested", "new.txt")));
        Assert.Empty(svc.ListBackups("nested/new.txt"));
        Assert.Null(result.BackupPath);
    }

    [Fact]
    public async Task Apply_OverMergeLimit_IsRejected()
    {
        var root = NewRoot();
        var svc = NewService(root, o => o.MaxMergeLines = 2);
        Write(root, "a.txt", "a\nb\nc\n");
        var before = await svc.SnapshotAsync("a.txt");
        Write(root, "a.txt", "a\nB\nc\n");

        var result = await svc.ApplyAsync(new FileEditRequest
        {
            Path = "a.txt",
            ExpectedSha256 = before.Sha256,
            BaseText = "a\nb\nc\n",
            NewText = "a\nb\nC\n",
            Source = "t11",
        });

        Assert.Equal(FileEditOutcome.Rejected, result.Outcome);
        Assert.Contains("上限", result.Note);
        Assert.Equal("a\nB\nc\n", Read(root, "a.txt"));
    }

    [Fact]
    public async Task Apply_SameContentTwice_SharesSingleBlob_AndRetentionPrunes()
    {
        var root = NewRoot();
        var svc = NewService(root, o => o.KeepPerFile = 1);
        Write(root, "a.txt", "v1\n");

        var s0 = await svc.SnapshotAsync("a.txt");
        await svc.ApplyAsync(new FileEditRequest { Path = "a.txt", ExpectedSha256 = s0.Sha256, NewText = "v2\n", Source = "t12" });
        var s1 = await svc.SnapshotAsync("a.txt");
        await svc.ApplyAsync(new FileEditRequest { Path = "a.txt", ExpectedSha256 = s1.Sha256, NewText = "v3\n", Source = "t12" });

        var backups = svc.ListBackups("a.txt");
        Assert.Single(backups);
        Assert.Equal(ContentHash.OfText("v2\n"), backups[0].Sha256);

        Write(root, "b.txt", "v2\n");
        var sb = await svc.SnapshotAsync("b.txt");
        await svc.ApplyAsync(new FileEditRequest { Path = "b.txt", ExpectedSha256 = sb.Sha256, NewText = "v9\n", Source = "t12" });
        Assert.Equal(backups[0].BlobPath, svc.ListBackups("b.txt")[0].BlobPath);
    }

    [Fact]
    public async Task Restore_RevertsByteForByte_AndBacksUpCurrentVersion()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "original\n");
        var s0 = await svc.SnapshotAsync("a.txt");
        await svc.ApplyAsync(new FileEditRequest { Path = "a.txt", ExpectedSha256 = s0.Sha256, NewText = "second\n", Source = "t13" });
        var s1 = await svc.SnapshotAsync("a.txt");
        await svc.ApplyAsync(new FileEditRequest { Path = "a.txt", ExpectedSha256 = s1.Sha256, NewText = "third\n", Source = "t13" });

        var oldest = svc.ListBackups("a.txt")[0];
        Assert.Equal(ContentHash.OfText("original\n"), oldest.Sha256);
        var restored = svc.Restore(oldest);

        Assert.Equal(FileEditOutcome.Applied, restored.Outcome);
        Assert.Equal("original\n", Read(root, "a.txt"));
        Assert.Equal(3, svc.ListBackups("a.txt").Count);
        Assert.Equal(ContentHash.OfText("third\n"), restored.BackupSha256);
    }

    [Fact]
    public async Task ConcurrentApplies_SameExpectedSha_SerialiseAndMergeWithoutLostUpdate()
    {
        var root = NewRoot();
        var svc = NewService(root);
        Write(root, "a.txt", "a\nb\nc\n");
        var before = await svc.SnapshotAsync("a.txt");
        var left = new FileEditRequest { Path = "a.txt", ExpectedSha256 = before.Sha256, BaseText = "a\nb\nc\n", NewText = "a\nB\nc\n", Source = "t14-left" };
        var right = new FileEditRequest { Path = "a.txt", ExpectedSha256 = before.Sha256, BaseText = "a\nb\nc\n", NewText = "a\nb\nC\n", Source = "t14-right" };

        var results = await Task.WhenAll(svc.ApplyAsync(left), svc.ApplyAsync(right));

        // 进程内互斥 ⇒ 必然一个走快路径、另一个走合并路径；两侧改动都不丢。
        var applied = 0;
        var merged = 0;
        foreach (var r in results)
        {
            if (r.Outcome == FileEditOutcome.Applied)
            {
                applied++;
            }
            else if (r.Outcome == FileEditOutcome.MergedAuto)
            {
                merged++;
            }
        }
        Assert.Equal(1, applied);
        Assert.Equal(1, merged);
        Assert.Equal("a\nB\nC\n", Read(root, "a.txt"));
        var backups = svc.ListBackups("a.txt");
        Assert.Equal(2, backups.Count);
        Assert.Equal(before.Sha256, backups[0].Sha256);
    }

    [Fact]
    public void Merge_NonOverlappingHunks_Clean_OverlappingHunks_Conflict()
    {
        var clean = ThreeWayLineMerge.Merge(
            new List<string> { "a", "b", "c", "d" },
            new List<string> { "a", "B", "c", "d" },
            new List<string> { "a", "b", "c", "D" },
            100);
        Assert.NotNull(clean);
        Assert.True(clean!.Clean);
        Assert.Equal(new List<string> { "a", "B", "c", "D" }, clean.MergedLines);

        var dirty = ThreeWayLineMerge.Merge(
            new List<string> { "a", "b", "c" },
            new List<string> { "a", "X", "c" },
            new List<string> { "a", "Y", "c" },
            100);
        Assert.NotNull(dirty);
        Assert.False(dirty!.Clean);
        Assert.Single(dirty.Conflicts);

        Assert.Null(ThreeWayLineMerge.Merge(
            new List<string> { "a", "b", "c" },
            new List<string> { "a", "X", "c" },
            new List<string> { "a", "Y", "c" },
            2));
    }

    [Fact]
    public void Registry_FallsBackToNative_AndUnavailablePluginIsNotUsed()
    {
        var empty = new FileServicePluginRegistry();
        Assert.Equal("native-local-file-service", empty.FirstAvailable()!.Name);
        Assert.NotNull(empty.Create(new FileServiceOptions()));

        var unavailable = new FileServicePluginRegistry(new IFileServicePlugin[] { new UnavailableFileServicePlugin() });
        Assert.Null(unavailable.FirstAvailable());
        Assert.Null(unavailable.Create(new FileServiceOptions()));
    }
}
