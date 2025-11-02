using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models
{
    public class GoogleCalendarEvent
    {
        [JsonPropertyName("title")]
        public string Title { get; set; }

        [JsonPropertyName("start")]
        public DateTime Start { get; set; }

        [JsonPropertyName("end")]
        public DateTime End { get; set; }
    }
}