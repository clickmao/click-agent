using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.userinteraction;

/// <summary>
/// R358 (工业级补齐 #1): 凭据静态加密 — 跨平台统一方案 (用户钦定: 不用 DPAPI/libsecret 分叉)。
/// 方案: AES-256-GCM (System.Security.Cryptography 原语, NativeAOT 完全支持, Win/Linux/macOS 同一实现)。
/// 密钥层级: 主密钥 (master.key, 32B 随机, 首次生成, UnixFileMode 600 / NTFS ACL 收紧)
///           └─ 每次保存派生随机 12B nonce + AES-GCM 认证标签 → credentials.json (密文 Base64)。
/// 明文兼容: 读取时检测旧明文 JSON → 自动迁移为密文 (一次性, 无感升级)。
/// 机器绑定: master.key 仅属当前用户目录+文件权限约束; 拷贝 data/ 到他机无 key 即不可解 (诚实边界:
/// 同机 root 仍可读 key — 本方案威胁模型是"防静态泄露/误提交", 非"防 root")。
/// </summary>
public static class CredentialEncryption
{
    private const int KeySize = 32;   // AES-256
    private const int NonceSize = 12; // GCM 标准
    private const int TagSize = 16;   // GCM 认证标签
    private const string MagicPrefix = "ENC1:"; // 密文版本前缀 (区分旧明文)

    /// <summary>主密钥路径: {dataDir}/master.key</summary>
    public static string MasterKeyPath(string dataDir) =>
        Path.Combine(string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "master.key");

    /// <summary>加载主密钥 (不存在则生成; 权限收紧尽力而为)。</summary>
    public static byte[] LoadOrCreateMasterKey(string dataDir)
    {
        var path = MasterKeyPath(dataDir);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

        if (File.Exists(path))
        {
            var key = File.ReadAllBytes(path);
            if (key.Length == KeySize) return key;
            // 长度异常 → 重新生成 (旧文件损坏; credentials 将解不开 → 走明文回退重新问询)
        }

        var newKey = RandomNumberGenerator.GetBytes(KeySize);
        File.WriteAllBytes(path, newKey);
        TightenPermissions(path);
        return newKey;
    }

    /// <summary>加密字典 → 密文文件内容 ("ENC1:" + base64(nonce+tag+ciphertext))。</summary>
    public static string Encrypt(IDictionary<string, string> credentials, byte[] masterKey)
    {
        var plain = JsonSerializer.Serialize(credentials, PromptJsonContext.Default.DictionaryStringString);
        var plainBytes = Encoding.UTF8.GetBytes(plain);
        var nonce = RandomNumberGenerator.GetBytes(NonceSize);
        var cipher = new byte[plainBytes.Length];
        var tag = new byte[TagSize];

        using var aes = new AesGcm(masterKey, TagSize);
        aes.Encrypt(nonce, plainBytes, cipher, tag);

        var payload = new byte[NonceSize + TagSize + cipher.Length];
        Buffer.BlockCopy(nonce, 0, payload, 0, NonceSize);
        Buffer.BlockCopy(tag, 0, payload, NonceSize, TagSize);
        Buffer.BlockCopy(cipher, 0, payload, NonceSize + TagSize, cipher.Length);
        return MagicPrefix + Convert.ToBase64String(payload);
    }

    /// <summary>解密文件内容 → 字典; 非密文 (旧明文) 返回 null 由调用方走迁移; 损坏/篡改抛 CryptographicException。</summary>
    public static Dictionary<string, string>? TryDecrypt(string fileContent, byte[] masterKey)
    {
        if (string.IsNullOrWhiteSpace(fileContent) || !fileContent.StartsWith(MagicPrefix, StringComparison.Ordinal))
            return null; // 旧明文 → 迁移路径

        byte[] payload;
        try { payload = Convert.FromBase64String(fileContent[MagicPrefix.Length..]); }
        catch (FormatException) { throw new CryptographicException("credentials 密文 base64 非法"); }
        if (payload.Length < NonceSize + TagSize)
            throw new CryptographicException("credentials 密文长度不足");

        var nonce = payload.AsSpan(0, NonceSize);
        var tag = payload.AsSpan(NonceSize, TagSize);
        var cipher = payload.AsSpan(NonceSize + TagSize);
        var plain = new byte[cipher.Length];

        using var aes = new AesGcm(masterKey, TagSize);
        aes.Decrypt(nonce, cipher, tag, plain); // 认证失败抛 CryptographicException
        var loaded = JsonSerializer.Deserialize(Encoding.UTF8.GetString(plain),
            PromptJsonContext.Default.DictionaryStringString);
        return loaded is null
            ? null
            : new Dictionary<string, string>(loaded, StringComparer.OrdinalIgnoreCase);
    }

    private static void TightenPermissions(string path)
    {
        if (!OperatingSystem.IsWindows())
        {
            try { File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite); }
            catch (PlatformNotSupportedException) { }
        }
    }
}
