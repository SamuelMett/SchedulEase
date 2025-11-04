namespace ScheduleEase.Client.Models
{
    public class ChatMessage
    {
        public string Content { get; set; } = "";
        public string UserId { get; set; } = "user"; // or "system"
        public bool IsUser { get; set; }
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public bool IsStreaming { get; set; }
    }
}
