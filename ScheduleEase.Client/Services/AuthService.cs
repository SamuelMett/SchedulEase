using SchedulEase.Models;

namespace SchedulEase.Services
{
    public class AuthService
    {
        private List<User> _users;
        public User? CurrentUser { get; private set; }

        public AuthService()
        {
            // Seeded users
            _users = new List<User>
            {
                new User
                {
                    Id = 1,
                    Email = "student@schedulease.com",
                    Password = "student123",
                    FullName = "John Student",
                    CreatedAt = DateTime.Now.AddMonths(-3)
                },
                new User
                {
                    Id = 2,
                    Email = "manager@schedulease.com",
                    Password = "manager123",
                    FullName = "Jane Manager",
                    CreatedAt = DateTime.Now.AddMonths(-6)
                },
                new User
                {
                    Id = 3,
                    Email = "admin@schedulease.com",
                    Password = "admin123",
                    FullName = "Admin User",
                    CreatedAt = DateTime.Now.AddYears(-1)
                }
            };
        }

        public bool SignIn(string email, string password)
        {
            var user = _users.FirstOrDefault(u => 
                u.Email.Equals(email, StringComparison.OrdinalIgnoreCase) && 
                u.Password == password);

            if (user != null)
            {
                CurrentUser = user;
                return true;
            }

            return false;
        }

        public bool SignUp(string email, string password, string fullName)
        {
            if (_users.Any(u => u.Email.Equals(email, StringComparison.OrdinalIgnoreCase)))
            {
                return false; // Email already exists
            }

            var newUser = new User
            {
                Id = _users.Max(u => u.Id) + 1,
                Email = email,
                Password = password,
                FullName = fullName,
                CreatedAt = DateTime.Now
            };

            _users.Add(newUser);
            CurrentUser = newUser;
            return true;
        }

        public void SignOut()
        {
            CurrentUser = null;
        }

        public bool IsAuthenticated => CurrentUser != null;

        public List<User> GetSeededUsers() => _users.Take(3).ToList();
    }
}