using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models
{
    // This represents an event extracted by the AI
    public class ScheduledEvent
    {
        [JsonPropertyName("title")]
        public string Title { get; set; }

        // Corresponds to evt.StartDate
        [JsonPropertyName("start_date")]
        public string StartDate { get; set; } // "YYYY-MM-DD"

        // Corresponds to evt.EndDate
        [JsonPropertyName("end_date")]
        public string? EndDate { get; set; } // "YYYY-MM-DD"

        // Corresponds to evt.Description
        [JsonPropertyName("description")]
        public string? Description { get; set; }
    }
}