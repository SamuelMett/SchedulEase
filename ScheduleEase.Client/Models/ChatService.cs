using System.Collections.Concurrent;
using ScheduleEase.Client.Models;

namespace ScheduleEase.Client.Services
{
    public static class ChatService
    {
        private static readonly ConcurrentDictionary<string, ChatSession> Sessions = new();

        public static ChatSession GetOrCreateSession(string sessionId)
        {
            return Sessions.GetOrAdd(sessionId, id => new ChatSession { SessionId = id });
        }

        public static void ClearSession(string sessionId)
        {
            if (Sessions.TryGetValue(sessionId, out var s))
                s.Messages.Clear();
        }

        public static async IAsyncEnumerable<string> GetCompletionsAsync(
            string userInput, string sessionId, CancellationToken ct,
            string? model = null, string? systemPrompt = null, double? temperature = null, int? maxTokens = null,
            string? endpoint = null, string? proxy = null, string? apiKey = null, string? apiKeyHeader = null)
        {
            var reply = userInput.ToLower().Contains("due") || userInput.Contains("assignment", StringComparison.OrdinalIgnoreCase)
                ? "You have 3 upcoming items: AI Lab 4 (Fri), UX Report (Sun), DBMS Project (Tue)."
                : userInput.ToLower().Contains("study")
                    ? "Here’s a focused study plan: \n1) 45m DBMS review\n2) 10m break\n3) 45m practice questions\n4) Summarize key points."
                    : "Got it! Ask about due dates, exams, or study plans any time.";

            foreach (var token in reply.Split(' '))
            {
                ct.ThrowIfCancellationRequested();
                await Task.Delay(50, ct);
                yield return token + " ";
            }

            var s = GetOrCreateSession(sessionId);
            s.Messages.Add(new ChatMessage { Content = userInput, IsUser = true, Timestamp = DateTime.Now });
            s.Messages.Add(new ChatMessage { Content = reply, IsUser = false, Timestamp = DateTime.Now });
        }
    }
}
