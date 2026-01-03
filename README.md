# Comrade Backend - Setup Guide

## Overview
Comrade is a comprehensive platform for academic collaboration, payment management, and research coordination.

## Quick Start

### 1. Environment Setup
```bash
# Clone and navigate
cd Comrade-Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
```

### 3. Database Setup
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Run Server
```bash
python manage.py runserver
```

Server will be available at: `http://localhost:8000`

---

## Environment Variables

### Required:
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode (True/False)
- `ALLOWED_HOSTS` - Comma-separated hosts

### Email (Required for auth):
- `EMAIL_HOST_USER` - SMTP email
- `EMAIL_HOST_PASSWORD` - App password

### OAuth (Optional):
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

### SMS/OTP (Optional):
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

---

## Apps Overview

### Authentication
- Custom user model with email login
- OAuth integration (Google, Facebook)
- JWT token authentication
- Role-based permissions

### Payment
- Payment profiles and balances
- Transaction management
- **Group savings** - collaborative payment pools
- **Contributions** - track member contributions
- **Standing orders** - recurring payments
- **Invitations** - invite users to groups

### Research
- Research project management
- Participant recruitment
- Compensation tracking
- Peer review system
- Publication management

### Other Apps
- UserManagement
- Rooms
- Announcements
- Events
- Resources
- Specialization
- Organisation
- Institution
- Task

---

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `GET /api/auth/verify/` - Email verification
- `GET /api/auth/google/` - Google OAuth
- `GET /api/auth/google/callback/` - OAuth callback

### Payment
- `GET /api/payments/profiles/my_profile/` - Get profile
- `GET /api/payments/profiles/balance/` - Check balance
- `POST /api/payments/transactions/create_transaction/` - Send money
- `GET /api/payments/transactions/history/` - Transaction history
- `GET /api/payments/groups/` - List groups
- `POST /api/payments/groups/` - Create group
- `POST /api/payments/groups/{id}/join/` - Join group
- `POST /api/payments/groups/{id}/contribute/` - Add contribution
- `POST /api/payments/groups/{id}/invite/` - Invite member

---

## Features

### Payment Groups
- Create savings pools
- Set target amounts
- Track contributions
- Auto-purchase when target reached
- Invite/approve members
- Standing orders for recurring payments

### Security
- Environment-based configuration
- Rate limiting on endpoints
- JWT token authentication
- Database indexes for performance
- Secure OAuth password generation

### Research
- Full research lifecycle
- Participant matching algorithm
- Compensation management
- Peer review workflow
- Publication system with DOI

---

## Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up Redis for caching
- [ ] Configure HTTPS
- [ ] Set secure cookie settings
- [ ] Configure static files
- [ ] Set up monitoring

### Recommended Stack
- **Server**: Gunicorn + Nginx
- **Database**: PostgreSQL
- **Cache**: Redis
- **Storage**: AWS S3 or similar

---

## Development

### Run Tests
```bash
python manage.py test
```

### Check Migration Status
```bash
python manage.py showmigrations
```

### Create App
```bash
python manage.py startapp appname
```

---

## Troubleshooting

### "No module named 'django'"
```bash
# Activate virtual environment first
venv\Scripts\activate
pip install django
```

### Migration conflicts
```bash
python manage.py migrate --fake-initial
```

### Port already in use
```bash
# Use different port
python manage.py runserver 8001
```

---

## Support
For issues or questions, check the TODO file or contact the development team.
