using Microsoft.AspNetCore.Components;
using ScheduleEase.Client.Models;  // <-- FIX 1: Changed from ScheduleEase.Models
using System.Net.Http.Json;

namespace ScheduleEase.Client.Pages    // <-- FIX 2: Changed from ScheduleEase.Pages
{
    public partial class MyCalendar
    {
        [Inject]
        private HttpClient Http { get; set; }

        protected IEnumerable<GoogleCalendarEvent> events;
        protected string errorMessage;

        protected override async Task OnInitializedAsync()
        {
            try
            {
                var result = await Http.GetFromJsonAsync<List<GoogleCalendarEvent>>("http://127.0.0.1:8000/calendar/events");

                if (result != null)
                {
                    events = result;
                }
                else
                {
                    errorMessage = "Could not load events.";
                }
            }
            catch (Exception ex)
            {
                errorMessage = $"Error loading events: {ex.Message}. Have you logged in?";
            }
        }
    }
}