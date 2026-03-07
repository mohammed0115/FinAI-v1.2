# FinAI Application Startup Guide

## Quick Start (2 minutes)

```bash
# 1. Make scripts executable
chmod +x run.sh quickstart.sh run-prod.sh

# 2. Run quick setup
./quickstart.sh

# 3. Start development server
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000

# 4. Open browser to http://localhost:8000
```

---

## Available Startup Methods

### 1. **Main run.sh Script** (Recommended)
The primary startup script with multiple modes:

```bash
./run.sh [MODE] [PORT]
```

**Available modes:**

- `dev` - Development server with auto-reload (default)
  ```bash
  ./run.sh dev 8000
  ```

- `prod` - Production server with Gunicorn
  ```bash
  ./run.sh prod 8000
  ```

- `migrate` - Run migrations only (no server)
  ```bash
  ./run.sh migrate
  ```

- `shell` - Open Django interactive shell
  ```bash
  ./run.sh shell
  ```

- `setup` - Initialize environment and exit
  ```bash
  ./run.sh setup
  ```

- `help` - Show all available options
  ```bash
  ./run.sh help
  ```

### 2. **Quickstart Script**
Fast setup for rapid development:

```bash
./quickstart.sh
```

This script:
- Creates virtual environment
- Installs dependencies
- Creates initial `.env` file
- Runs migrations
- Exits (you manually start server)

### 3. **Production Startup**
Optimized for production deployments:

```bash
./run-prod.sh
```

Sets up and starts with Gunicorn, logging to `logs/` directory.

Configuration via environment variables:
```bash
PORT=8000 WORKERS=4 TIMEOUT=30 ./run-prod.sh
```

### 4. **Makefile Commands**
Convenient shortcuts for common tasks:

```bash
# Show all available commands
make help

# Common commands
make install          # Install dependencies
make migrate          # Run migrations
make run              # Start dev server
make prod             # Start prod server
make shell            # Open Django shell
make clean            # Clean cache files
make test             # Run tests
make lint             # Run code linting
make collectstatic    # Collect static files
```

---

## Environment Setup

### Create `.env` File

```bash
# The .env file is required (should be in backend/ directory)
# A template is provided in the repo

# Edit with your settings:
nano .env
```

**Key settings to configure:**

```env
# Debug mode (False in production!)
DEBUG=True

# Secret key (change in production!)
SECRET_KEY=your-secret-key-here

# Database
DATABASE_ENGINE=django.db.backends.sqlite3    # or postgresql
DATABASE_NAME=db.sqlite3                      # or your_db_name

# OpenAI (for Phase 5 financial narratives)
OPENAI_API_KEY=sk-your-api-key-here

# Allowed hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# Environment
ENVIRONMENT=development                       # or production
```

See [.env template](./backend/.env) for complete configuration options.

---

## Development Workflow

### Start Development Server

```bash
./run.sh dev 8000
```

- Runs on `http://localhost:8000`
- Auto-reloads on file changes
- Press `Ctrl+C` to stop

### Test the Application

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose

# Run specific test
python manage.py test core.tests.TestVATValidation
```

### Access Django Shell

```bash
./run.sh shell
# or
make shell
```

Interactive Python shell with Django models imported.

### Database Management

```bash
# Create admin user
make createsuperuser

# View migrations status
make showmigrations

# Reset database (⚠️ WARNING: deletes all data!)
make reset-db

# Export data
make dumpdata FILE=backup.json

# Import data
make loaddata FILE=backup.json
```

### Code Quality

```bash
# Lint code (flake8)
make lint

# Format code (black)
make format

# Sort imports (isort)
make isort

# All at once
make lint && make format && make isort
```

---

## Production Deployment

### Option 1: Using run-prod.sh

```bash
# Start production server
./run-prod.sh

# With custom configuration
PORT=8080 WORKERS=8 TIMEOUT=60 ./run-prod.sh
```

Logs are saved to `logs/` directory:
- `logs/production.log` - Main application log
- `logs/access.log` - HTTP access logs
- `logs/error.log` - Error logs

### Option 2: Using Systemd Service

Create `/etc/systemd/system/finai.service`:

```ini
[Unit]
Description=FinAI Application
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/FinAI-v1.2/backend
EnvironmentFile=/path/to/FinAI-v1.2/backend/.env
ExecStart=/path/to/FinAI-v1.2/backend/venv/bin/gunicorn \
    FinAI.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 30
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl start finai
sudo systemctl enable finai
sudo systemctl status finai
```

### Option 3: Using Supervisor

Create `/etc/supervisor/conf.d/finai.conf`:

```ini
[program:finai]
command=/path/to/venv/bin/gunicorn \
    FinAI.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 30
directory=/path/to/FinAI-v1.2/backend
user=www-data
environment=PATH="/path/to/venv/bin"
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/finai.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status finai
```

### Option 4: Using Docker

See [Docker deployment guide](../DOCKER_SETUP.md)

---

## Pre-Production Checklist

Before running in production:

- [ ] Edit `.env` file with production values
- [ ] Set `DEBUG=False`
- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Use PostgreSQL instead of SQLite
- [ ] Run migrations: `./run.sh migrate`
- [ ] Collect static files: `make collectstatic`
- [ ] Test with production settings: `python manage.py check --deploy`
- [ ] Configure HTTPS/SSL
- [ ] Set up log directory with proper permissions
- [ ] Configure email for notifications
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Load test the application
- [ ] Have rollback plan ready

---

## Troubleshooting

### Port Already in Use

```bash
# See what's using the port
lsof -i :8000

# Use a different port
./run.sh dev 3000
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
./quickstart.sh
```

### Database Errors

```bash
# Reset database and migrations
make reset-db
make migrate
```

### Missing Dependencies

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### OpenAI API Issues

Financial narratives (Phase 5) will auto-fallback to rule-based if OpenAI is unavailable. Check:
- `.env` has valid `OPENAI_API_KEY`
- API key has usage quota remaining
- Network connectivity to OpenAI

---

## Performance Notes

- **Development mode**: 1-3 seconds per request (with auto-reload)
- **Production mode**: <100ms for cached requests
- **OpenAI integration**: 2-5 seconds per narrative generation
- **Database queries**: Optimize with `.select_related()` and `.prefetch_related()`
- **Static files**: Pre-collected and served by reverse proxy (Nginx/Apache)

---

## Monitoring & Health Checks

### Application Health

```bash
# Check application status
make health

# Run system checks
python manage.py check

# Check for deployment issues
python manage.py check --deploy
```

### View Logs

```bash
# Development
tail -f logs/django.log

# Production
tail -f logs/production.log
tail -f logs/error.log

# Access logs
tail -f logs/access.log
```

### Database Health

```bash
# Check database connection
python manage.py dbshell

# Backup database
python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

---

## Getting Help

- **Script help**: `./run.sh help` or `make help`
- **Django help**: `python manage.py help <command>`
- **Check logs**: `tail -f logs/django.log`
- **Interactive debugging**: `./run.sh shell`

---

## Quick Reference

| Task | Command |
|------|---------|
| Start dev | `./run.sh dev` or `make run` |
| Start prod | `./run.sh prod` or `make prod` |
| Migrations | `./run.sh migrate` or `make migrate` |
| Django shell | `./run.sh shell` or `make shell` |
| Create admin | `make createsuperuser` |
| Run tests | `make test` |
| View logs | `make logs` |
| Clean cache | `make clean` |
| Format code | `make format` |
| Stop server | `Ctrl+C` |

---

## Next Steps

1. ✅ Created startup scripts (run.sh, quickstart.sh, run-prod.sh)
2. ✅ Created Makefile with commands
3. ✅ Created .env configuration file
4. **→ Update .env with your settings**
5. **→ Run: `./quickstart.sh` to initialize**
6. **→ Run: `./run.sh dev` to start development**
7. → Create admin user: `make createsuperuser`
8. → Access admin: `http://localhost:8000/admin/`
9. → Start developing!

---

## Documentation References

- [FinAI README](../README.md)
- [Phase 5 Implementation Guide](../PHASE_5_IMPLEMENTATION_GUIDE.md)
- [Phase 5 Deployment Checklist](../PHASE_5_QUICK_DEPLOYMENT_CHECKLIST.md)
- [Django Documentation](https://docs.djangoproject.com/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)

---

**Last Updated**: March 6, 2026
**FinAI Version**: 1.2
