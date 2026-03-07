# FinAI Startup Quick Reference

## Files Created

```
backend/
├── .env                          # Environment configuration (edit with your settings)
├── run.sh                        # Main startup script (all modes, recommended)
├── quickstart.sh                 # Quick setup script (for fast setup)
├── run-prod.sh                   # Production startup with Gunicorn
├── Makefile                      # Make commands (convenient shortcuts)
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker compose orchestration
├── .dockerignore                 # Files to ignore in Docker build
├── nginx.conf                    # Nginx reverse proxy configuration
├── STARTUP_GUIDE.md              # Complete startup documentation
└── DOCKER_DEPLOYMENT_GUIDE.md    # Docker deployment guide
```

---

## Quick Start Commands

### Development (2 steps)

```bash
# Step 1: Quick setup
./quickstart.sh

# Step 2: Start server
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

Or use main script:
```bash
./run.sh dev 8000
```

### Production (1 step)

```bash
./run-prod.sh
```

### Using Makefile

```bash
make run              # Start dev server
make prod             # Start prod server
make migrate          # Run migrations
make help             # Show all commands
```

### Using Docker

```bash
docker-compose build  # Build images
docker-compose up -d  # Start services
docker-compose logs -f web  # View logs
```

---

## File Reference

| File | Purpose | Usage |
|------|---------|-------|
| `.env` | Configuration | Edit with your settings before starting |
| `run.sh` | Main launcher | `./run.sh dev\|prod\|migrate\|shell\|help` |
| `quickstart.sh` | Fast setup | `./quickstart.sh` |
| `run-prod.sh` | Production server | `./run-prod.sh` |
| `Makefile` | Make commands | `make help` for all options |
| `Dockerfile` | Docker image | Part of `docker-compose.yml` |
| `docker-compose.yml` | Container stack | `docker-compose up -d` |
| `nginx.conf` | Web server config | Used by Docker only |
| `STARTUP_GUIDE.md` | Full documentation | Read for detailed info |
| `DOCKER_DEPLOYMENT_GUIDE.md` | Docker docs | Read for Docker deployment |

---

## Mode Selector

### Choose Your Mode

**Just want to run FinAI?**
```bash
./run.sh dev
```

**Want to contribute/develop?**
```bash
./quickstart.sh
source venv/bin/activate
python manage.py runserver
```

**Running in production?**
```bash
./run-prod.sh
```

**Using Docker?**
```bash
docker-compose up -d
```

**Like Makefile shortcuts?**
```bash
make run    # or make prod
```

---

## What Each Script Does

### `run.sh` (Main Script)
- **Purpose**: Universal startup script with multiple modes
- **Best for**: Production, development, migrations, debugging
- **Modes**: `dev`, `prod`, `migrate`, `shell`, `setup`, `help`
- **Example**: `./run.sh dev 3000` (start on port 3000)
- **Features**: Auto setup, migrations, venv activation

### `quickstart.sh` (Fast Setup)
- **Purpose**: Rapid environment initialization
- **Best for**: First-time setup, quick demos
- **Time**: ~2-3 minutes
- **What it does**: venv + dependencies + migrations
- **After**: Run `python manage.py runserver` manually

### `run-prod.sh` (Production)
- **Purpose**: Production-grade server startup
- **Best for**: Deployment, production clusters
- **Web Server**: Gunicorn (handles multiple workers)
- **Logging**: Saves to `logs/` directory
- **Environment vars**: `PORT`, `WORKERS`, `TIMEOUT`

### `Makefile` (Convenience)
- **Purpose**: Common development commands
- **Best for**: Developers who prefer `make` style
- **Top commands**:
  - `make run` - Start dev
  - `make prod` - Start production
  - `make migrate` - Run migrations
  - `make test` - Run tests
  - `make help` - Show all

### `docker-compose.yml` (Containers)
- **Purpose**: Full stack with PostgreSQL, Redis, Nginx
- **Best for**: Docker deployments, isolated environments
- **Services**: 5 containers (Django, PostgreSQL, Redis, Nginx, Health)
- **Command**: `docker-compose up -d`

---

## Configuration Checklist

Before running, configure:

- [ ] Edit `.env` file
  - Set `SECRET_KEY` to random value
  - Set `DEBUG=False` for production
  - Configure database credentials
  - Add `OPENAI_API_KEY` if using Phase 5

- [ ] Run migrations
  - `./run.sh migrate` OR
  - `make migrate` OR
  - `docker-compose exec web python manage.py migrate`

- [ ] Create admin user (optional)
  - `make createsuperuser` OR
  - `docker-compose exec web python manage.py createsuperuser`

---

## Common Tasks

| Task | Command |
|------|---------|
| Start dev server | `./run.sh dev` OR `make run` |
| Start prod server | `./run.sh prod` OR `make prod` |
| Run migrations | `./run.sh migrate` OR `make migrate` |
| Django shell | `./run.sh shell` OR `make shell` |
| Create admin | `make createsuperuser` |
| View logs | `make logs` OR `docker-compose logs -f` |
| Run tests | `make test` |
| Format code | `make format` |
| Stop server | `Ctrl+C` |
| Stop Docker | `docker-compose down` |

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| Django Dev | 8000 | Development server (auto-reload) |
| Django Prod | 8000+ | Production with Gunicorn |
| Nginx | 80 | Web server (Docker) |
| PostgreSQL | 5432 | Database (Docker) |
| Redis | 6379 | Cache (Docker) |
| Admin | /admin/ | Django admin panel |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8000 in use | `./run.sh dev 3000` (use diff port) |
| `.env` not found | Copy from template or edit `.env` |
| Dependencies missing | `pip install -r requirements.txt` |
| Database error | `./run.sh migrate` |
| Docker won't start | `docker-compose build --no-cache` |
| Permission denied | `chmod +x *.sh` |

---

## Next Steps

1. **Edit `.env`** - Configure your environment
2. **Choose startup method**:
   - Quick: `./quickstart.sh`
   - Dev: `./run.sh dev`
   - Prod: `./run-prod.sh`
   - Docker: `docker-compose up -d`
3. **Create admin user**: `make createsuperuser`
4. **Open browser**: http://localhost:8000
5. **Start developing!**

---

## Documentation Links

- **Local Startup**: [STARTUP_GUIDE.md](./STARTUP_GUIDE.md)
- **Docker Deployment**: [DOCKER_DEPLOYMENT_GUIDE.md](./DOCKER_DEPLOYMENT_GUIDE.md)
- **Phase 5 Implementation**: [../PHASE_5_IMPLEMENTATION_GUIDE.md](../PHASE_5_IMPLEMENTATION_GUIDE.md)
- **Phase 5 Checklist**: [../PHASE_5_QUICK_DEPLOYMENT_CHECKLIST.md](../PHASE_5_QUICK_DEPLOYMENT_CHECKLIST.md)
- **Main README**: [../README.md](../README.md)

---

## Support

For detailed documentation, see:
- `STARTUP_GUIDE.md` - Complete startup reference
- `DOCKER_DEPLOYMENT_GUIDE.md` - Docker deployment details
- `.env` file - Configuration options
- `Makefile` - All available commands via `make help`

Run `./run.sh help` for command reference.

---

**Version**: FinAI 1.2
**Last Updated**: March 6, 2026
