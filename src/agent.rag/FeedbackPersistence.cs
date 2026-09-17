using Microsoft.Extensions.Logging;
using System.Text.Json;

namespace agent.rag;


/// <summary>
/// 用户反馈持久化实现
/// </summary>
public class FeedbackPersistence : IFeedbackPersistence
{
    private readonly ILogger<FeedbackPersistence> _logger;
    private readonly IRAGRecall _ragRecall;
    private readonly Dictionary<string, UserFeedback> _feedbackStore = new();
    private readonly object _lock = new();
    
    public FeedbackPersistence(ILogger<FeedbackPersistence> logger, IRAGRecall ragRecall)
    {
        _logger = logger;
        _ragRecall = ragRecall;
    }
    
    public async Task SaveAsync(UserFeedback feedback)
    {
        if (string.IsNullOrEmpty(feedback.Id))
        {
            feedback.Id = Guid.NewGuid().ToString();
        }
        
        lock (_lock)
        {
            _feedbackStore[feedback.Id] = feedback;
        }
        
        // 索引到RAG
        var doc = new RAGDocument
        {
            Id = $"feedback_{feedback.Id}",
            Content = $"Task: {feedback.TaskDescription}\nContext: {feedback.Context}\nComment: {feedback.UserComment}\nOutcome: {feedback.Outcome}",
            Summary = $"{feedback.SelectedOptionLabel}: {feedback.TaskDescription}",
            Keywords = feedback.Keywords,
            DocumentType = "user_feedback",
            Metadata = new Dictionary<string, object>
            {
                { "feedbackId", feedback.Id },
                { "taskId", feedback.TaskId },
                { "sessionId", feedback.SessionId },
                { "selectedOption", feedback.SelectedOptionLabel ?? "" },
                { "outcome", feedback.Outcome ?? "" }
            }
        };
        
        await _ragRecall.IndexAsync(doc);
        
        _logger.LogInformation("Saved feedback {FeedbackId} and indexed to RAG", feedback.Id);
    }
    
    public async Task<List<RecallResult>> QuerySimilarAsync(string query, int topK = 5)
    {
        var request = new RecallRequest
        {
            Query = query,
            DocumentType = "user_feedback",
            TopK = topK
        };
        
        return await _ragRecall.RecallAsync(request);
    }
    
    public Task<List<UserFeedback>> GetByTaskAsync(string taskId)
    {
        lock (_lock)
        {
            var feedbacks = _feedbackStore.Values
                .Where(f => f.TaskId == taskId)
                .OrderByDescending(f => f.CreatedAt)
                .ToList();
            
            return Task.FromResult(feedbacks);
        }
    }
    
    public Task<List<UserFeedback>> GetBySessionAsync(string sessionId)
    {
        lock (_lock)
        {
            var feedbacks = _feedbackStore.Values
                .Where(f => f.SessionId == sessionId)
                .OrderByDescending(f => f.CreatedAt)
                .ToList();
            
            return Task.FromResult(feedbacks);
        }
    }
    
    public Task UpdateOutcomeAsync(string feedbackId, string outcome, double? satisfaction = null)
    {
        lock (_lock)
        {
            if (_feedbackStore.TryGetValue(feedbackId, out var feedback))
            {
                feedback.Outcome = outcome;
                feedback.Satisfaction = satisfaction;
            }
        }
        
        return Task.CompletedTask;
    }
}
