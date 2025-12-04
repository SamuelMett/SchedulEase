using ScheduleEase.Client.Models;

namespace ScheduleEase.Client.Services
{
    public class ChatSession
    {
        public string SessionId { get; set; } = "";
        public List<ChatMessage> Messages { get; set; } = new();
    }
}
