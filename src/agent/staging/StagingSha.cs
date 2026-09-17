using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.staging;

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
