# AlumniConnect - AI-Powered Alumni Management System

A comprehensive Django-based platform connecting alumni, students, and faculty for mentorship, job referrals, and career growth.

## Tech Stack

- **Backend**: Django 5.x + Django REST Framework
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Frontend**: Django Templates + Tailwind CSS + Vanilla JS
- **Database**: PostgreSQL
- **Cache/Queue**: Redis + Celery
- **Real-time**: Django Channels + Redis
- **AI**: OpenAI API (GPT-4o-mini)
- **Payments**: Razorpay
- **File Processing**: PyPDF2, python-docx

## Features

- 4 User Roles: Alumni, Student, Faculty, Admin
- Job Referrals & Applications
- Paid Mentorship Sessions (1:1 Bookings)
- AI Resume Scorer & Builder
- AI Mock Interviews
- Course Recommendations
- Revenue Dashboard (30% platform, 70% earner)
- Real-time Notifications
- Payment Integration with Razorpay

## Project Structure

```
alumni_platform/
├── apps/
│   ├── accounts/          # User authentication & profiles
│   ├── feed/              # Posts & comments
│   ├── sessions_app/      # Mentorship sessions & bookings
│   ├── referrals/         # Job referrals & applications
│   ├── payments/          # Transactions & wallet
│   ├── ai_tools/          # AI-powered tools
│   ├── dashboard/         # Admin analytics
│   └── notifications/     # Notification system
├── alumni_platform/
│   ├── settings/          # Split settings (base, dev, prod)
│   ├── celery.py          # Celery configuration
│   └── urls.py            # Main URL routing
└── templates/             # HTML templates
```


## Setup Instructions

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd alumni_platform
```

2. **Create and activate virtual environment**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your configuration
# - SECRET_KEY
# - Database credentials
# - Redis URL
# - OpenAI API key
# - Razorpay credentials
# - Email settings
```

5. **Database Setup**
```bash
# Create PostgreSQL database
createdb alumni_db

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

6. **Create Superuser**
```bash
python manage.py createsuperuser
```

7. **Collect Static Files**
```bash
python manage.py collectstatic --noinput
```

8. **Run Development Server**
```bash
python manage.py runserver
```

Visit http://localhost:8000

### Running Celery (Separate Terminal)

```bash
# Celery Worker
celery -A alumni_platform worker -l info

# Celery Beat (for scheduled tasks)
celery -A alumni_platform beat -l info
```

### Running Redis

```bash
redis-server
```

## API Endpoints

- `/api/token/` - Obtain JWT token
- `/api/token/refresh/` - Refresh JWT token
- `/api/accounts/` - User management
- `/api/feed/` - Social feed
- `/api/sessions/` - Mentorship sessions
- `/api/referrals/` - Job referrals
- `/api/payments/` - Payment processing
- `/api/ai/` - AI tools
- `/api/dashboard/` - Analytics
- `/api/notifications/` - Notifications

## Development

- Admin Panel: http://localhost:8000/admin
- Debug Toolbar: Enabled in development mode
- API Documentation: Coming soon

## License

MIT License
