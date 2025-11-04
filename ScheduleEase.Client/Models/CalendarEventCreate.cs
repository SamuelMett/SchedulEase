using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models
{
    // This is used to POST a new event to the /api/calendar/events endpoint
    public class CalendarEventCreate
    {
        [JsonPropertyName("title")]
        public string Title { get; set; }

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("start")]
        public DateTime Start { get; set; } // Full DateTime

        [JsonPropertyName("end")]
        public DateTime End { get; set; } // Full DateTime
    }
}