using agent.roles;
using Xunit;

namespace agent.tests;

/// <summary>
/// R363/R364: .rbin 单文件格式 (非明文/压缩/快读快写/可扩展) + 失败簇 (推理中止→赏罚)。
/// </summary>
public class RoleBinaryFileTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "rbin_" + Guid.NewGuid().ToString("N"));
    public RoleBinaryFileTests() { Directory.CreateDirectory(_dir); }
    public void Dispose() { if (Directory.Exists(_dir)) Directory.Delete(_dir, true); }

    private static byte[] Key() => System.Security.Cryptography.RandomNumberGenerator.GetBytes(32);

    [Fact]
    public void 往返_全字段保真()
    {
        var key = Key();
        var doc = new RoleBinaryFile.RoleDocument
        {
            Id = "skeptic", Name = "疑问者", ProfileSeed = "你是追问者", TokensUsed = 42,
            Growth = new Dictionary<string, (int, int)>(StringComparer.OrdinalIgnoreCase)
                { ["docker"] = (0, 5), ["git"] = (3, 0) },
            Extra = new Dictionary<string, string> { ["custom"] = "v1" },
        };
        var path = Path.Combine(_dir, "t.rbin");
        RoleBinaryFile.Write(path, doc, key);
        var back = RoleBinaryFile.Read(path, key);

        Assert.Equal("skeptic", back.Id);
        Assert.Equal("疑问者", back.Name);
        Assert.Equal("你是追问者", back.ProfileSeed);
        Assert.Equal(42, back.TokensUsed);
        Assert.Equal((0, 5), back.Growth["docker"]);
        Assert.Equal((3, 0), back.Growth["git"]);
        Assert.Equal("v1", back.Extra["custom"]); // 扩展区
    }

    [Fact]
    public void 非明文_文件无种子文本()
    {
        var key = Key();
        var path = Path.Combine(_dir, "t.rbin");
        RoleBinaryFile.Write(path, new RoleBinaryFile.RoleDocument
            { Id = "x", Name = "机密人格", ProfileSeed = "SECRET-PERSONA-TEXT- Marks" }, key);
        var raw = File.ReadAllBytes(path);
        var text = System.Text.Encoding.UTF8.GetString(raw);
        Assert.DoesNotContain("SECRET-PERSONA-TEXT", text); // 明文不可见
        Assert.DoesNotContain("机密人格", text);
    }

    [Fact]
    public void 篡改_认证拒绝()
    {
        var key = Key();
        var path = Path.Combine(_dir, "t.rbin");
        RoleBinaryFile.Write(path, new RoleBinaryFile.RoleDocument { Id = "x" }, key);
        var raw = File.ReadAllBytes(path);
        raw[^1] ^= 0xFF;
        File.WriteAllBytes(path, raw);
        Assert.ThrowsAny<System.Security.Cryptography.CryptographicException>(
            () => RoleBinaryFile.Read(path, key));
    }

    [Fact]
    public void 错误密钥_解密失败()
    {
        var path = Path.Combine(_dir, "t.rbin");
        RoleBinaryFile.Write(path, new RoleBinaryFile.RoleDocument { Id = "x" }, Key());
        Assert.ThrowsAny<System.Security.Cryptography.CryptographicException>(
            () => RoleBinaryFile.Read(path, Key()));
    }

    [Fact]
    public void 非法magic_拒载()
    {
        var path = Path.Combine(_dir, "bad.rbin");
        File.WriteAllBytes(path, "NOTARBIN"u8.ToArray());
        Assert.ThrowsAny<InvalidDataException>(() => RoleBinaryFile.Read(path, Key()));
    }

    [Fact]
    public void 压缩有效_重复文本_体积小于明文一半()
    {
        var key = Key();
        var path = Path.Combine(_dir, "t.rbin");
        var doc = new RoleBinaryFile.RoleDocument
        {
            Id = "big", Name = "n",
            ProfileSeed = string.Concat(System.Linq.Enumerable.Repeat("这是一段重复的测试文本。", 40)), // 明文 ~880B
        };
        RoleBinaryFile.Write(path, doc, key);
        Assert.True(new FileInfo(path).Length < 880 / 2, $"压缩后 {new FileInfo(path).Length}B 应 < 明文一半");
    }
}
