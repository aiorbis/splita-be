# Splita Backend - Personal Finance Management System

A comprehensive Django REST API backend for managing credit cards, loans, and EMI scheduling with automated notifications.

## Features

### 🔐 User Management
- JWT-based authentication with refresh tokens
- User registration, login, and profile management
- Session tracking with device information
- FCM token management for push notifications

### 💳 Credit Card Management
- Add, update, and manage credit cards
- Track credit utilization and balances
- Automatic EMI generation for credit card payments
- Credit limit monitoring and alerts

### 🏦 Loan Management
- Comprehensive loan tracking (personal, home, auto, etc.)
- EMI schedule generation and management
- Loan completion percentage tracking
- Remaining balance calculations

### 📅 EMI Scheduler
- Automatic EMI schedule generation based on start date
- Monthly EMI calculations with proper date progression
- Overdue EMI detection and management
- Payment tracking and status updates

### 🔔 Notification System
- Multi-channel notifications (Email, Push, SMS)
- Template-based notification system
- User preference management
- Automated reminders for:
  - Upcoming EMI payments
  - Overdue payments
  - High credit utilization alerts

### 📊 Dashboard & Analytics
- Comprehensive financial dashboard
- Credit card and loan summaries
- EMI overview and statistics
- Payment history tracking

## Tech Stack

- **Backend**: Django 4.2.21 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (Simple JWT)
- **Task Queue**: Celery + Redis
- **Notifications**: Firebase Cloud Messaging
- **Image Processing**: Pillow

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Git

## Installation & Setup

### Option 1: Docker Setup (Recommended)

The easiest way to get started is using Docker:

```bash
git clone <repository-url>
cd splita-be

# Start development environment
./docker-setup.sh dev

# Or manually with docker-compose
cp env.docker .env
docker-compose up -d
```

**Access Points:**
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Database: localhost:5432
- Redis: localhost:6379

For detailed Docker instructions, see [DOCKER.md](DOCKER.md).

### Option 2: Manual Setup

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd splita-be
```

#### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` file with your configuration:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DB_NAME=splita_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# Firebase (for notifications)
FIREBASE_SERVER_KEY=your-firebase-server-key
```

#### 5. Database Setup

Create PostgreSQL database:

```sql
CREATE DATABASE splita_db;
CREATE USER postgres WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE splita_db TO postgres;
```

Run migrations:

```bash
cd splita
python manage.py makemigrations
python manage.py migrate
```

#### 6. Create Superuser

```bash
python manage.py createsuperuser
```

#### 7. Run Automated Setup (Recommended)

Use the automated setup script to initialize the database and create initial data:

```bash
python setup.py
```

This script will:
- Create and run all database migrations
- Set up notification templates
- Prompt you to create a superuser account

#### 8. Manual Setup (Alternative)

If you prefer manual setup:

```bash
cd splita
python manage.py makemigrations
python manage.py migrate
python manage.py create_notification_templates
python manage.py createsuperuser
```

#### 9. Start Development Server

```bash
cd splita
python manage.py runserver
```

#### 10. Start Celery Worker (Optional)

For background tasks and notifications:

```bash
# In a new terminal
cd splita
celery -A splita worker -l info
```

### 11. Start Celery Beat (Optional)

For scheduled tasks:

```bash
# In another terminal
cd splita
celery -A splita beat -l info
```

### 12. Test the API (Optional)

Run the comprehensive API test suite:

```bash
python test_api.py
```

## API Endpoints

### Authentication (`/api/accounts/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/` | User registration |
| POST | `/login/` | User login |
| POST | `/logout/` | User logout |
| POST | `/token/refresh/` | Refresh JWT token |
| GET/PUT | `/profile/` | User profile management |
| POST | `/change-password/` | Change password |
| GET | `/sessions/` | List user sessions |
| POST | `/fcm-token/` | Update FCM token |
| GET | `/dashboard/` | User dashboard |

### Credit Cards (`/api/credit-cards/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/` | List/Create credit cards |
| GET/PUT/DELETE | `/{id}/` | Credit card details |
| GET | `/{id}/details/` | Credit card with EMIs and summary |
| GET | `/{id}/emis/` | List EMIs for credit card |
| POST | `/{id}/emis/create/` | Create EMI for credit card |
| GET | `/{id}/emis/enhanced/` | Enhanced EMI list |
| POST | `/{id}/emis/generate-schedule/` | Generate EMI schedule |
| GET | `/{id}/emis/summary/` | EMI summary for credit card |
| GET | `/emis/{id}/` | EMI details |
| POST | `/emis/{id}/mark-paid/` | Mark EMI as paid |
| GET | `/emis/enhanced/` | All credit card EMIs (enhanced) |
| GET/POST | `/payments/` | List/Create payments |
| GET | `/payments/{id}/` | Payment details |
| GET | `/summary/` | Credit card summary |

### Loans (`/api/loans/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/` | List/Create loans |
| GET/PUT/DELETE | `/{id}/` | Loan details |
| GET | `/{id}/details/` | Loan with EMIs and summary |
| GET | `/{id}/emis/` | List EMIs for loan |
| POST | `/{id}/emis/create/` | Create EMI for loan |
| GET | `/{id}/emis/enhanced/` | Enhanced EMI list |
| POST | `/{id}/emis/generate-schedule/` | Generate EMI schedule |
| GET | `/{id}/emis/summary/` | EMI summary for loan |
| GET | `/emis/{id}/` | EMI details |
| POST | `/emis/{id}/mark-paid/` | Mark EMI as paid |
| GET | `/emis/enhanced/` | All loan EMIs (enhanced) |
| GET/POST | `/payments/` | List/Create payments |
| GET | `/payments/{id}/` | Payment details |
| GET | `/summary/` | Loan summary |

### Dashboard (`/api/dashboard/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Combined dashboard with credit cards and loans |
| GET | `/enhanced/` | Enhanced dashboard for mobile app |

### Notifications (`/api/notifications/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List notifications |
| GET | `/{id}/` | Notification details |
| POST | `/{id}/mark-read/` | Mark notification as read |
| POST | `/mark-all-read/` | Mark all notifications as read |
| GET/PUT | `/preferences/` | Notification preferences |
| GET | `/stats/` | Notification statistics |
| GET | `/templates/` | List templates (Admin) |
| POST | `/trigger/` | Trigger notification (Admin) |

## Project Structure

```
splita-be/
├── splita/
│   ├── accounts/           # User management app
│   ├── credit_cards/       # Credit card management
│   ├── loans/              # Loan management
│   ├── dashboard/          # Combined dashboard
│   ├── notifications/      # Notification system
│   ├── splita/            # Main project settings
│   └── manage.py
├── requirements.txt
├── env.example
└── README.md
```

## Key Models

### User Model
- Extended AbstractUser with additional fields
- Email as username field
- Profile picture, phone number, FCM token

### Credit Card Model
- Card details, credit limit, current balance
- Automatic utilization percentage calculation
- Linked EMIs for payment tracking

### Loan Model
- Principal amount, interest rate, tenure
- Current balance and completion percentage
- Automatic EMI generation

### EMI Model
- Linked to credit cards or loans
- Due date tracking and overdue detection
- Payment status management

### Payment Model
- Payment tracking against EMIs
- Multiple payment methods support
- Transaction reference tracking

## Background Tasks

The system includes several Celery tasks for automation:

- **EMI Reminders**: Send notifications before EMI due dates
- **Overdue Alerts**: Alert users about overdue payments
- **Credit Utilization**: Monitor and alert high utilization
- **Cleanup Tasks**: Remove old notifications and sessions

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

The project follows PEP 8 guidelines. Use tools like `black` and `flake8` for code formatting.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Deployment

For production deployment:

1. Set `DEBUG=False` in environment
2. Configure proper database settings
3. Set up static file serving
4. Configure Redis for production
5. Set up proper logging
6. Use environment variables for sensitive data

## License

This project is licensed under the MIT License.

## Admin Interface

The system includes a comprehensive Django admin interface with the following features:

### Admin Features
- **User Management**: View and manage user accounts, sessions, and verification status
- **Credit Card Management**: Monitor credit cards, utilization, and limits
- **Loan Management**: Track loans, completion percentages, and payment schedules
- **EMI Management**: View EMI schedules, payment status, and overdue tracking
- **Payment Tracking**: Monitor all payments with transaction details
- **Notification Management**: Manage notification templates, preferences, and delivery status
- **Bulk Actions**: Mark notifications as read/sent, manage user sessions

### Admin Access
Access the admin interface at `http://localhost:8000/admin/` using your superuser credentials.

## Additional Features

### Notification Templates
The system comes with pre-configured notification templates for:
- EMI payment reminders
- Payment confirmations
- Overdue payment alerts
- Credit utilization warnings
- Loan completion notifications
- Welcome messages

### Background Tasks
Automated Celery tasks handle:
- Daily EMI reminders based on user preferences
- Overdue payment alerts
- Credit utilization monitoring
- Notification cleanup
- Pending notification retry

### API Testing
Use the included test script to validate all endpoints:
```bash
python test_api.py [base_url]
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - Verify database exists

2. **Celery Tasks Not Running**
   - Ensure Redis is running
   - Check Redis connection in settings
   - Start Celery worker and beat processes

3. **Push Notifications Not Working**
   - Verify Firebase server key in `.env`
   - Check user FCM token is set
   - Ensure Firebase project is configured

4. **Email Notifications Not Sending**
   - Configure email backend in settings
   - Set proper SMTP credentials
   - Check email template configuration

## Support

For support and questions, please create an issue in the repository. 