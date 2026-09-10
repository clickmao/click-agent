using agent.userinteraction;
using Xunit;

namespace agent.tests;

/// <summary>R358 (工业级 #1): 凭据静态加密 — AES-256-GCM 跨平台统一方案。</summary>
public class CredentialEncryptionTests : IDisposable
{
    private readonly string _dir;
    public CredentialEncryptionTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "credeg_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_dir);
    }
    public void Dispose()
    {
        if (Directory.Exists(_dir)) Directory.Delete(_dir, true);
    }

    [Fact]
    public void 加解密往返_保序保值()
    {
        var key = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        var src = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["ApiKey"] = "sk-test-123", ["endpoint"] = "http://localhost:8080",
        };
        var enc = CredentialEncryption.Encrypt(src, key);
        Assert.StartsWith("ENC1:", enc);

        var dec = CredentialEncryption.TryDecrypt(enc, key)!;
        Assert.Equal(2, dec.Count);
        Assert.Equal("sk-test-123", dec["apikey"]); // 大小写不敏感键
        Assert.Equal("http://localhost:8080", dec["endpoint"]);
    }

    [Fact]
    public void 密文不可重放nonce_两次加密不同()
    {
        var key = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        var src = new Dictionary<string, string> { ["k"] = "v" };
        Assert.NotEqual(CredentialEncryption.Encrypt(src, key), CredentialEncryption.Encrypt(src, key));
    }

    [Fact]
    public void 篡改密文_GCM认证拒绝()
    {
        var key = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        var enc = CredentialEncryption.Encrypt(new Dictionary<string, string> { ["k"] = "secret-value" }, key);
        var b64 = enc["ENC1:".Length..];
        var payload = Convert.FromBase64String(b64);
        payload[^1] ^= 0xFF; // 翻转密文最后 1 bit
        var tampered = "ENC1:" + Convert.ToBase64String(payload);

        Assert.ThrowsAny<System.Security.Cryptography.CryptographicException>(
            () => CredentialEncryption.TryDecrypt(tampered, key));
    }

    [Fact]
    public void 错误密钥_解密失败不泄明文()
    {
        var dir2 = _dir + "_2";
        Directory.CreateDirectory(dir2);
        var key1 = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        var key2 = CredentialEncryption.LoadOrCreateMasterKey(dir2);
        Assert.NotEqual(key1, key2);
        var enc = CredentialEncryption.Encrypt(new Dictionary<string, string> { ["k"] = "v" }, key1);
        Assert.ThrowsAny<System.Security.Cryptography.CryptographicException>(
            () => CredentialEncryption.TryDecrypt(enc, key2));
    }

    [Fact]
    public void 旧明文内容_返回null走迁移路径()
    {
        var key = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        Assert.Null(CredentialEncryption.TryDecrypt("{\"k\":\"v\"}", key));
        Assert.Null(CredentialEncryption.TryDecrypt("", key));
    }

    [Fact]
    public void 主密钥_持久化复用()
    {
        var k1 = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        var k2 = CredentialEncryption.LoadOrCreateMasterKey(_dir);
        Assert.Equal(k1, k2);
        Assert.True(File.Exists(CredentialEncryption.MasterKeyPath(_dir)));
    }
}
