using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.staging;

/// <summary>v0.17.1 (R335, 用户钦定): 离线变更批次中的单个文件项 — 完整快照存 staging (git index 简化版)。
/// Path=真实目标; BaselineSha=批次创建时目标文件哈希 (apply 时比对 — 用户已改/正编辑 → 冲突拒绝, 绝不覆盖);
/// ContentFile=staging 内完整新内容文件 (不占用真实地址, 编辑器零感知); Applied=逐项应用状态 (批次可 partial)。</summary>
public sealed class StagedItem
{
    public string Path { get; set; } = "";
    public string BaselineSha { get; set; } = "";
    public string ContentFile { get; set; } = "";
    public bool Applied { get; set; }
}

/// <summary>v0.17.1: 变更批次。Status: pending → approved(全应用)/partial(部分冲突)/rejected/expired。</summary>
public sealed class ChangeBatch
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..12];
    public string Source { get; set; } = "agent";
    public string Status { get; set; } = "pending";
    public long CreatedUnixMs { get; set; }
    public long UpdatedUnixMs { get; set; }
    public int TtlDays { get; set; } = 7;
    public List<StagedItem> Items { get; set; } = new();

    public bool IsPending => Status == "pending";
}

/// <summary>sha256 工具 (BCL IncrementalHash — AOT 安全)。</summary>
public static class StagingSha
{
    public static string OfFile(string path)
    {
        if (!File.Exists(path)) return "";
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        using var fs = File.OpenRead(path);
        var buf = new byte[81920];
        int n;
        while ((n = fs.Read(buf, 0, buf.Length)) > 0) h.AppendData(buf, 0, n);
        return Convert.ToHexString(h.GetHashAndReset()).ToLowerInvariant();
    }

    public static string OfBytes(ReadOnlySpan<byte> data)
    {
        using var h = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        h.AppendData(data);
        return Convert.ToHexString(h.GetHashAndReset()).ToLowerInvariant();
    }
}
