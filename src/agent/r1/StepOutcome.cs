namespace agent.r1;

/// <summary>
/// R1 管道 · 单步执行读数（每个 plan 节点一行，含产物 sha/字节数，供机械判分与产物守恒核对）。
/// Rc = -9 表示超时被杀（非进程退出码，显式区分，禁与真实 rc 混算）。
/// </summary>
public sealed record StepOutcome(
    string Id,
    string Tool,
    int Rc,
    string Path,
    string Sha256,
    long Bytes,
    string StdoutTail,
    string StderrTail,
    int ElapsedMs)
{
    public static StepOutcome None(string id) => new(id, "none", 0, string.Empty, string.Empty, 0, string.Empty, string.Empty, 0);

    public static StepOutcome Write(string id, string path, string sha256, long bytes) =>
        new(id, "write_file", 0, path, sha256, bytes, string.Empty, string.Empty, 0);

    public static StepOutcome Run(string id, int rc, string stdoutTail, string stderrTail, int elapsedMs) =>
        new(id, "run", rc, string.Empty, string.Empty, 0, stdoutTail, stderrTail, elapsedMs);
}
