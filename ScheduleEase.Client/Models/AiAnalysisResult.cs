using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models
{
    public class AiAnalysisResult
    {
        // Corresponds to aiResult.Summary
        [JsonPropertyName("summary")]
        public string Summary { get; set; }

        // Corresponds to aiResult.Events
        [JsonPropertyName("events")]
        public List<ScheduledEvent> Events { get; set; }
    }
}