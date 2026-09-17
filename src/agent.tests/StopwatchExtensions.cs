using agent.core;
using agent.session;
using Microsoft.Extensions.Logging;
using Xunit;
using Xunit.Abstractions;

namespace agent.tests;


public static class StopwatchExtensions
{
    public static long ElapsedMicroseconds(this System.Diagnostics.Stopwatch sw) =>
        sw.ElapsedTicks * 1_000_000 / System.Diagnostics.Stopwatch.Frequency;
}
