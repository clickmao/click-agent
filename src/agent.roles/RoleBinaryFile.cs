using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Security.Cryptography;
using System.Text;

namespace agent.roles;

/// <summary>
/// R363 (v0.21.0 修订, 用户钦定): Role 单文件外挂格式 — .rbin。
/// 目录方案废除; 唯一形态 = 单文件, 非明文, 压缩友好, 快读快写, 可扩展。
///
/// 文件结构 (全部小端):
///   bytes 0-3   magic "ARBL" (AgentFramework Role Binary, v1)
///   bytes 4     format version = 1
///   bytes 5     flags (bit0: payload 已加密)
///   bytes 6-7   保留
///   bytes 8-11  payload 压缩后长度 (uint32)
///   bytes 12-15 payload 解压后长度 (uint32)
///   bytes 16+   payload = [AES-GCM(nonce12|tag16|cipher)] 包裹的 gzip( JSON 文档 )
///
/// payload 内 JSON (UTF-8, 字典即文档, 可扩展 — 未知键读取时保留):
///   { "id": "skeptic", "name": "疑问者", "profile": "种子语料",
///     "growth": { "docker": {"r":0,"p":5}, ... }, "tokens": 0,
///     "ext": { ...任意自定义键值 (保留扩展区) } }
///
/// 快读快写: 读 = 单次 File.ReadAllBytes + 内存解压 (无流扫描); 写 = 全量序列化 + File.WriteAllBytes
/// (临时文件+rename 原子替换)。目标体量 KB 级, 全量读写远快于增量。
/// 非明文: 双层 — gzip 消除文本特征 + AES-256-GCM 加密 (密钥层级复用 CredentialEncryption master.key)。
/// </summary>
public static class RoleBinaryFile
{
    private const uint Magic = 0x4C425241; // "ARBL" little-endian
    private const byte Version = 1;
    private const int HeaderSize = 16;
    private const byte FlagEncrypted = 0x01;

    /// <summary>文档模型 — 外部 API 的读写载体 (可扩展: Extra 保留未知键)。</summary>
    public sealed class RoleDocument
    {
        public string Id { get; set; } = "";
        public string Name { get; set; } = "";
        /// <summary>人格种子语料 (可空 — 无种子时 Role 仅由赏罚动态构成)</summary>
        public string ProfileSeed { get; set; } = "";
        /// <summary>域赏罚账本 (domain → 赏/罚) — 与 GrowthLedger 互转</summary>
        public Dictionary<string, (int Reward, int Penalty)> Growth { get; set; } = new(StringComparer.OrdinalIgnoreCase);
        public int TokensUsed { get; set; }
        /// <summary>扩展区 (未识别键保留 — 版本兼容)</summary>
        public Dictionary<string, string> Extra { get; set; } = new(StringComparer.Ordinal);
    }

    // ── 写 (原子替换) ──
    public static void Write(string path, RoleDocument doc, byte[] masterKey)
    {
        var json = JsonSerializer.Serialize(ToPayload(doc), PayloadJsonContext.Default.DictionaryStringString);
        var plain = Encoding.UTF8.GetBytes(json);

        // gzip 预压 (消除文本特征 + 压缩友好)
        byte[] compressed = Compress(plain);

        // AES-GCM 加密 (nonce12 | tag16 | cipher)
        var nonce = RandomNumberGenerator.GetBytes(12);
        var cipher = new byte[compressed.Length];
        var tag = new byte[16];
        using (var aes = new AesGcm(masterKey, 16))
            aes.Encrypt(nonce, compressed, cipher, tag);
        var payload = new byte[12 + 16 + cipher.Length];
        Buffer.BlockCopy(nonce, 0, payload, 0, 12);
        Buffer.BlockCopy(tag, 0, payload, 12, 16);
        Buffer.BlockCopy(cipher, 0, payload, 28, cipher.Length);

        // header (16B) + payload
        using var ms = new MemoryStream(HeaderSize + payload.Length);
        using (var w = new BinaryWriter(ms, Encoding.UTF8, leaveOpen: true))
        {
            w.Write(Magic);
            w.Write(Version);
            w.Write(FlagEncrypted);
            w.Write((ushort)0);
            w.Write((uint)payload.Length);
            w.Write((uint)compressed.Length);
        }
        ms.Write(payload);

        // 原子替换 (tmp + rename) — 对齐 AtomicFileWriter 语义
        var tmp = path + ".tmp";
        File.WriteAllBytes(tmp, ms.ToArray());
        if (File.Exists(path)) File.Replace(tmp, path, null);
        else File.Move(tmp, path);
    }

    // ── 读 ──
    public static RoleDocument Read(string path, byte[] masterKey)
    {
        var bytes = File.ReadAllBytes(path);
        if (bytes.Length < HeaderSize || BitConverter.ToUInt32(bytes, 0) != Magic)
            throw new InvalidDataException($"非 ARBL 文件: {path}");
        var version = bytes[4];
        if (version != Version)
            throw new InvalidDataException($"ARBL 版本不支持: {version}");
        var flags = bytes[5];
        var payloadLen = BitConverter.ToUInt32(bytes, 8);
        var compressedLen = BitConverter.ToUInt32(bytes, 12);

        var payload = new byte[payloadLen];
        Buffer.BlockCopy(bytes, HeaderSize, payload, 0, (int)payloadLen);

        byte[] compressed;
        if ((flags & FlagEncrypted) != 0)
        {
            var nonce = payload.AsSpan(0, 12);
            var tag = payload.AsSpan(12, 16);
            var cipher = payload.AsSpan(28);
            compressed = new byte[cipher.Length];
            using var aes = new AesGcm(masterKey, 16);
            aes.Decrypt(nonce, cipher, tag, compressed); // 篡改/密钥错 → CryptographicException
        }
        else compressed = payload;

        if (compressed.Length != compressedLen)
            throw new InvalidDataException("解压后长度与头不符");

        var plain = Decompress(compressed);
        var payloadDict = JsonSerializer.Deserialize(plain, PayloadJsonContext.Default.DictionaryStringString)
            ?? throw new InvalidDataException("payload JSON 非法");
        return FromPayload(payloadDict);
    }

    // ── payload ↔ 文档 (扁平键, 可扩展: 未知 "x:" 前缀键进 Extra) ──
    internal static Dictionary<string, string> ToPayload(RoleDocument d)
    {
        var p = new Dictionary<string, string>
        {
            ["id"] = d.Id,
            ["name"] = d.Name,
            ["profile"] = d.ProfileSeed,
            ["tokens"] = d.TokensUsed.ToString(),
        };
        foreach (var (domain, s) in d.Growth)
            p[$"g:{domain}"] = $"{s.Reward}|{s.Penalty}";
        foreach (var (k, v) in d.Extra)
            p[$"x:{k}"] = v;
        return p;
    }

    internal static RoleDocument FromPayload(Dictionary<string, string> p)
    {
        var d = new RoleDocument
        {
            Id = p.GetValueOrDefault("id", ""),
            Name = p.GetValueOrDefault("name", ""),
            ProfileSeed = p.GetValueOrDefault("profile", ""),
            TokensUsed = int.TryParse(p.GetValueOrDefault("tokens"), out var t) ? t : 0,
        };
        foreach (var (k, v) in p)
        {
            if (k.StartsWith("g:", StringComparison.Ordinal))
            {
                var parts = v.Split('|');
                d.Growth[k[2..]] = (int.Parse(parts[0]), int.Parse(parts[1]));
            }
            else if (k.StartsWith("x:", StringComparison.Ordinal))
                d.Extra[k[2..]] = v;
        }
        return d;
    }

    internal static byte[] Compress(ReadOnlySpan<byte> data)
    {
        using var ms = new MemoryStream();
        using (var gz = new GZipStream(ms, CompressionLevel.SmallestSize))
            gz.Write(data);
        return ms.ToArray();
    }

    internal static byte[] Decompress(byte[] data)
    {
        using var inMs = new MemoryStream(data);
        using var gz = new GZipStream(inMs, CompressionMode.Decompress);
        using var outMs = new MemoryStream();
        gz.CopyTo(outMs);
        return outMs.ToArray();
    }
}

/// <summary>AOT source-gen (payload 是扁平 string→string 字典)。</summary>
[JsonSerializable(typeof(Dictionary<string, string>))]
internal sealed partial class PayloadJsonContext : JsonSerializerContext;
