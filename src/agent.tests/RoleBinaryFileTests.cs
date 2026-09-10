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

/// <summary>R364: 失败簇 — 推理中止赏罚。</summary>
public class FailureClustersTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "fc_" + Guid.NewGuid().ToString("N"));
    public FailureClustersTests() { Directory.CreateDirectory(_dir); }
    public void Dispose() { if (Directory.Exists(_dir)) Directory.Delete(_dir, true); }

    [Fact]
    public void 罚分达阈值_注入警告()
    {
        var fc = new FailureClusters(_dir);
        for (var i = 0; i < 3; i++) fc.RecordAbort("timeout", "如何求解非线性偏微分方程组");
        var warn = fc.RenderWarning("如何求解非线性偏微分方程组");
        Assert.Contains("推理中止", warn);
    }

    [Fact]
    public void 罚分不足_无警告()
    {
        var fc = new FailureClusters(_dir);
        fc.RecordAbort("timeout", "冷门问题甲");
        Assert.Equal(string.Empty, fc.RenderWarning("冷门问题甲的解法"));
    }

    [Fact]
    public void 不同主题_不串簇()
    {
        var fc = new FailureClusters(_dir);
        for (var i = 0; i < 5; i++) fc.RecordAbort("stagnation", "docker 网络配置问题反复出现");
        Assert.Equal(string.Empty, fc.RenderWarning("git rebase 的正确流程是什么"));
    }

    [Fact]
    public void 落盘重载_簇保持()
    {
        var fc1 = new FailureClusters(_dir);
        for (var i = 0; i < 3; i++) fc1.RecordAbort("timeout", "复现某崩溃问题");
        var fc2 = new FailureClusters(_dir); // 新实例=重启
        Assert.Contains("推理中止", fc2.RenderWarning("复现某崩溃问题"));
    }

    [Fact]
    public void 停滞检测_重复回复判真_变化判假()
    {
        var same = new[] { "方案如下: 使用 A", "方案如下: 使用 A", "方案如下: 使用 A" };
        Assert.True(FailureClusters.IsStagnant(same));
        var diff = new[] { "方案如下: 使用 A", "方案如下: 使用 B", "方案如下: 使用 A" };
        Assert.False(FailureClusters.IsStagnant(diff));
    }
}
