using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.llmservice;

namespace agent.llamalocal;


public static class EmbedderMode
{
    public const string EnvName = "AGENTFRAMEWORK_BGE_MODE";

    public static EmbedderModeKind Resolve(string? envValue)
        => string.Equals(envValue?.Trim(), "remote", StringComparison.OrdinalIgnoreCase)
            ? EmbedderModeKind.Remote
            : EmbedderModeKind.Local;
}
