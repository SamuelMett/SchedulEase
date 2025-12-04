using System.Text.Json.Serialization;

namespace ScheduleEase.Client.Models
{
    public class StudyMaterial
    {
        [JsonPropertyName("id")]
        public string Id { get; set; }

        [JsonPropertyName("eventTitle")]
        public string EventTitle { get; set; }

        [JsonPropertyName("eventDate")]
        public DateTime EventDate { get; set; }

        [JsonPropertyName("content")]
        public string Content { get; set; }

        [JsonPropertyName("createdAt")]
        public DateTime CreatedAt { get; set; }
    }

    public class GenerateStudyMaterialRequest
    {
        [JsonPropertyName("eventTitle")]
        public string EventTitle { get; set; }

        [JsonPropertyName("eventStart")]
        public DateTime EventStart { get; set; }

        [JsonPropertyName("eventEnd")]
        public DateTime EventEnd { get; set; }
    }
}