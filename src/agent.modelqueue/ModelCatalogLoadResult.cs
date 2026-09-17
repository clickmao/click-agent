using agent.config;

namespace agent.modelqueue;


/// <summary>DI 载体: 目录 + 加载来源快照 (避免重复解析; Router/Balance/Verify 共享同一实例)</summary>
public sealed class ModelCatalogLoadResult
{
    public ModelCatalog Catalog { get; }

    private ModelCatalogLoadResult(ModelCatalog catalog) => Catalog = catalog;

    public static ModelCatalogLoadResult Wrap(ModelCatalog catalog, ConfigSnapshot snapshot) =>
        new(catalog);
}
