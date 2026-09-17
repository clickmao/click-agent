using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Logging;

namespace agent.userinteraction;

/// <summary>
/// 凭据/审批的本地持久化存储 —— 凭据只落本地加密目录权限文件, 绝不进日志/上下文。
/// </summary>
public static class PromptPersistence
{
    /// <summary>凭据文件路径: {dataDir}/credentials.json (用户主动提供的 Key 存这里, 下次启动复用)</summary>
    public static string CredentialsPath(string dataDir) =>
        Path.Combine(string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "credentials.json");

    /// <summary>审批策略缓存路径</summary>
    public static string ApprovalCachePath(string dataDir) =>
        Path.Combine(string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "approval_cache.json");

    public static Dictionary<string, string> LoadCredentials(string dataDir)
    {
        var path = CredentialsPath(dataDir);
        if (!File.Exists(path))
            return new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        try
        {
            var content = File.ReadAllText(path);

            // R358: 密文路径 (ENC1: 前缀) — AES-GCM 解密; 密钥缺失/损坏 → 空表重新问询
            if (content.StartsWith("ENC1:", StringComparison.Ordinal))
            {
                var key = CredentialEncryption.LoadOrCreateMasterKey(dataDir);
                var decrypted = CredentialEncryption.TryDecrypt(content, key);
                return decrypted is null
                    ? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                    : new Dictionary<string, string>(decrypted, StringComparer.OrdinalIgnoreCase);
            }

            // 旧明文 JSON → 读取并一次性迁移为密文 (无感升级)
            var loaded = JsonSerializer.Deserialize(content, PromptJsonContext.Default.DictionaryStringString);
            var result = loaded is null
                ? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                : new Dictionary<string, string>(loaded, StringComparer.OrdinalIgnoreCase);
            if (result.Count > 0)
            {
                try { SaveCredentials(dataDir, result); } catch { /* 迁移失败不影响本次读取 */ }
            }
            return result;
        }
        catch
        {
            // 凭据文件损坏 (含 GCM 认证失败 = 篡改/密钥不匹配) → 视为无凭据, 重新问询 (绝不抛异常阻断启动)
            return new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        }
    }

    public static void SaveCredentials(string dataDir, Dictionary<string, string> credentials)
    {
        var path = CredentialsPath(dataDir);
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        // R358: 静态加密落盘 (AES-256-GCM; 主密钥 master.key 与文件分离)
        var masterKey = CredentialEncryption.LoadOrCreateMasterKey(dataDir);
        File.WriteAllText(path, CredentialEncryption.Encrypt(credentials, masterKey));

        // 尽力收紧文件权限 (Unix); Windows 上 ACL 收紧交给用户/部署脚本
        if (!OperatingSystem.IsWindows())
        {
            try
            {
                File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            }
            catch (PlatformNotSupportedException)
            {
            }
        }
    }

    /// <summary>审计日志: 每次问询/代答/自动批准都追加一行 (JSONL), 供事后追责</summary>
    public static void AppendAudit(string dataDir, PromptAuditEntry entry)
    {
        try
        {
            var path = Path.Combine(
                string.IsNullOrWhiteSpace(dataDir) ? "." : dataDir, "prompt_audit.jsonl");
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir))
                Directory.CreateDirectory(dir);
            File.AppendAllText(path, JsonSerializer.Serialize(entry, PromptJsonContext.Default.PromptAuditEntry) + Environment.NewLine);
        }
        catch
        {
            // 审计失败不阻断主流程
        }
    }
}
