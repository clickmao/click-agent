namespace agent.recall;


public sealed class RecallScanOptions
{
    public bool PruneUnchangedDirs { get; init; } = true;
    public long NowTicks { get; init; } = DateTime.UtcNow.Ticks;
    public string[] SkipDirectoryNames { get; init; } = Array.Empty<string>();
    public string[] IncludeFileNameSuffixes { get; init; } = Array.Empty<string>();
    public string StoreFileName { get; init; } = "fingerprints.bin";
}
