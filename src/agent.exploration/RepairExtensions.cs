namespace agent.exploration;


internal static class RepairExtensions
{
    public static TOut Let<TIn, TOut>(this TIn v, Func<TIn, TOut> f) => f(v);
}
