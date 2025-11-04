using Microsoft.AspNetCore.Components;
using ScheduleEase.Client.Models;
using System.Net.Http.Json;
// --- 1. ADD THIS USING STATEMENT ---
using Microsoft.AspNetCore.Components.WebAssembly.Http;

namespace ScheduleEase.Client.Pages
{
    public partial class MyCalendar
    {
        [Inject]
        private HttpClient Http { get; set; }

        protected IEnumerable<GoogleCalendarEvent> events;
        protected string errorMessage;

        // --- 2. THIS METHOD IS UPDATED ---
        protected override async Task OnInitializedAsync()
        {
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Get, "http://127.0.0.1:8000/calendar/events");
                request.SetBrowserRequestCredentials(BrowserRequestCredentials.Include);


                // Send the custom request
                var response = await Http.SendAsync(request);

                if (response.IsSuccessStatusCode)
                {
                    // Manually read the JSON and convert it to our event list
                    events = await response.Content.ReadFromJsonAsync<List<GoogleCalendarEvent>>();
                }
                else
                {
                    // Handle non-success statuses (like a 401 if the cookie is invalid)
                    errorMessage = $"Error loading events: {response.ReasonPhrase}. Have you logged in?";
                }
            }
            catch (Exception ex)
            {
                // This will catch network errors (like the original 'Failed to fetch')
                errorMessage = $"Error loading events: {ex.Message}. Is the backend running?";
            }
        }
    }
}