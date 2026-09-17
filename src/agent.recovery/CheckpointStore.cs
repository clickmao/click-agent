using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.recovery;


/// <summary>
/// 检查点仓库: 写 (执行器每节点边界回调) + 读 (启动/恢复时) + 恢复裁定。
/// 线程安全 (单文件锁)。
/// </summary>
public sealed class CheckpointStore
{
    private readonly string _sessionsDir;
    private readonly object _lock = new();

    public CheckpointStore(string dataStoragePath = "data")
    {
        _sessionsDir = Path.Combine(dataStoragePath, "sessions");
        Directory.CreateDirectory(_sessionsDir);
    }

    private string PathOf(string sessionId) =>
        Path.Combine(_sessionsDir, sessionId, "checkpoint.json");

    /// <summary>保存检查点 (原子写: 同目录 tmp → move 覆盖 — 崩溃不产生半截文件)。</summary>
    public void Save(ExecutionCheckpoint checkpoint)
    {
        lock (_lock)
        {
            var finalPath = PathOf(checkpoint.SessionId);
            Directory.CreateDirectory(Path.GetDirectoryName(finalPath)!);
            var tmpPath = finalPath + ".tmp";
            File.WriteAllText(tmpPath,
                JsonSerializer.Serialize(checkpoint, RecoveryJsonContext.Default.ExecutionCheckpoint));
            File.Move(tmpPath, finalPath, overwrite: true);
        }
    }

    /// <summary>读取最近检查点 (无 → null)。</summary>
    public ExecutionCheckpoint? Load(string sessionId)
    {
        lock (_lock)
        {
            var path = PathOf(sessionId);
            if (!File.Exists(path))
                return null;
            try
            {
                return JsonSerializer.Deserialize(
                    File.ReadAllText(path), RecoveryJsonContext.Default.ExecutionCheckpoint);
            }
            catch (System.Text.Json.JsonException)
            {
                // 半截/损坏文件 (理论上原子写避免, 但历史文件可能) → 按无检查点处理, 不阻断启动
                return null;
            }
        }
    }

    /// <summary>清除检查点 (计划成功跑完/用户显式 /reset 时调用)。</summary>
    public void Clear(string sessionId)
    {
        lock (_lock)
        {
            var path = PathOf(sessionId);
            if (File.Exists(path))
                File.Delete(path);
        }
    }
}
