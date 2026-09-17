namespace agent.datastore;


/// <summary>
/// 数据存储接口
/// </summary>
public interface IDataStore
{
    Task<DataEntry> SaveAsync(DataEntry entry);
    Task<DataEntry?> GetAsync(string key);
    Task<IEnumerable<DataEntry>> QueryAsync(DataQuery query);
    Task DeleteAsync(string key);
    Task<bool> ExistsAsync(string key);
    Task<IEnumerable<string>> GetCategoriesAsync();
}
