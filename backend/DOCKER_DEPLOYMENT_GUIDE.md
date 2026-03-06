# FinAI Docker Deployment Guide

## Overview

This guide covers deploying FinAI using Docker and Docker Compose. The stack includes:
- **Django Application** (Gunicorn)
- **PostgreSQL Database**
- **Redis Cache**
- **Nginx Reverse Proxy**

---

## Prerequisites

- Docker Desktop or Docker Engine (v20.10+)
- Docker Compose (v2.0+)
- 2GB+ RAM available
- `.env` file configured in `backend/` directory

Install:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Quick Start

### 1. Prepare Environment

```bash
cd backend/

# Create .env file if not exists
cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=finai_db
DATABASE_USER=finai_user
DATABASE_PASSWORD=finai_password
DATABASE_HOST=db
DATABASE_PORT=5432
OPENAI_API_KEY=sk-your-api-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
ENVIRONMENT=production
EOF
```

### 2. Build Images

```bash
docker-compose build
```

This builds the custom Django image. PostgreSQL and Nginx are pulled from Docker Hub.

### 3. Start Services

```bash
docker-compose up -d
```

Services start in daemon mode:
- `db` - PostgreSQL on port 5432
- `redis` - Redis cache on port 6379
- `web` - Django/Gunicorn on port 8000 (internal)
- `nginx` - Nginx on port 80

### 4. Verify Services

```bash
# Check running containers
docker-compose ps

# Check logs
docker-compose logs web

# Health check
docker-compose exec web curl http://localhost:8000/health/
```

### 5. Create Admin User

```bash
docker-compose exec web python manage.py createsuperuser
```

### 6. Access Application

- **Web**: http://localhost
- **Admin**: http://localhost/admin/
- **API**: http://localhost/api/

---

## Common Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web

# Last 100 lines
docker-compose logs -f --tail 100 web

# Follow errors only
docker-compose logs -f web | grep ERROR
```

### Stop Services

```bash
# Stop but keep containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove volumes too (⚠️ deletes data!)
docker-compose down -v
```

### Database Operations

```bash
# PostgreSQL shell
docker-compose exec db psql -U finai_user -d finai_db

# Backup database
docker-compose exec db pg_dump -U finai_user finai_db > backup.sql

# Restore database
docker-compose exec -T db psql -U finai_user finai_db < backup.sql
```

### Running Management Commands

```bash
# Migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Django shell
docker-compose exec web python manage.py shell_plus

# Run tests
docker-compose exec web python manage.py test
```

### Scaling Services

```bash
# Scale web workers (requires load balancer, not recommended for single instance)
docker-compose up -d --scale web=3

# Better: adjust WORKERS env variable for Gunicorn
docker-compose set-env web WORKERS=8
```

---

## Production Setup

### 1. Configure Environment

Edit `backend/.env` for production:

```env
DEBUG=False
SECRET_KEY=<strong-random-key>
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=finai_db
DATABASE_USER=finai_user
DATABASE_PASSWORD=<strong-password>
DATABASE_HOST=db
DATABASE_PORT=5432
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ENVIRONMENT=production
OPENAI_API_KEY=sk-your-api-key
```

### 2. Configure HTTPS

Edit `nginx.conf` to enable SSL/TLS:

```bash
# Generate self-signed certificate (for testing)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# Or use Let's Encrypt with Certbot
```

### 3. Update docker-compose.yml

```yaml
# Add volume for SSL certificates
volumes:
  - ./ssl:/etc/nginx/ssl:ro

# Update nginx ports
ports:
  - "443:443"
  - "80:80"  # For redirects
```

### 4. Start with Monitoring

```bash
# Use systemd unit
cat > /etc/systemd/system/finai.service << 'EOF'
[Unit]
Description=FinAI Docker Application
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/path/to/backend
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable finai
sudo systemctl start finai
```

---

## Monitoring & Maintenance

### Health Checks

All services have health checks configured:

```bash
# Check service health
docker-compose ps

# Manual health check
curl http://localhost/health/
```

### Backup Strategy

```bash
# Daily database backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/finai"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T db pg_dump -U finai_user finai_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
EOF

chmod +x backup.sh
```

### Resource Monitoring

```bash
# Monitor container resource usage
docker stats

# Persistent monitoring with Portainer
docker run -d -p 8080:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  portainer/portainer-ce:latest
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs web

# Verify image built
docker images | grep finai

# Rebuild
docker-compose build --no-cache web
```

### Database Connection Error

```bash
# Ensure db container is healthy
docker-compose exec db psql -U finai_user -d finai_db -c "SELECT 1"

# Check environment variables
docker-compose config | grep DATABASE_
```

### Static Files Not Found

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check nginx volume
docker-compose exec nginx ls -la /app/staticfiles/
```

### Permission Denied Errors

Ensure the `finai` user (UID 1000) has permission to volumes:

```bash
# Fix permissions
sudo chown -R 1000:1000 media/ logs/
```

### Out of Memory

Increase Docker memory limit or adjust in docker-compose.yml:

```yaml
web:
  deploy:
    resources:
      limits:
        memory: 2G
```

---

## Development with Docker

### Enable Hot Reload

Edit `docker-compose.yml` for web service:

```yaml
web:
  command: python manage.py runserver 0.0.0.0:8000
  volumes:
    - .:/app  # Mount entire backend directory
```

Then rebuild and restart:

```bash
docker-compose down
docker-compose up -d
```

### Debug Mode

Enable Django debugger:

```bash
# Run with interactive shell
docker-compose run --rm web python manage.py shell

# Or use pdb
# In your code: import pdb; pdb.set_trace()
docker-compose run --service-ports web python manage.py runserver 0.0.0.0:8000
```

---

## Performance Tuning

### Database Optimization

```bash
# Connect to PostgreSQL
docker-compose exec db psql -U finai_user -d finai_db

# Create indexes
CREATE INDEX idx_invoice_organization ON documents_invoice(organization_id);
CREATE INDEX idx_vat_validation_invoice ON core_vatvalidation(invoice_id);
```

### Gunicorn Workers

Edit `docker-compose.yml`:

```yaml
web:
  environment:
    - WORKERS=8  # Adjust based on CPU cores
```

### Redis Max Memory

```bash
# Limit Redis memory
docker-compose exec redis redis-cli CONFIG SET maxmemory 256mb
```

---

## Production Deployment Checklist

- [ ] `.env` configured with production values
- [ ] `DEBUG=False` set
- [ ] Strong `SECRET_KEY` configured
- [ ] HTTPS/SSL enabled and configured
- [ ] Database backups automated
- [ ] Log rotation configured
- [ ] Monitoring/alerting set up
- [ ] Resource limits defined
- [ ] Health checks verified
- [ ] Database indices created
- [ ] Static files collected
- [ ] Tested failover/recovery
- [ ] Load testing completed

---

## Clean Up

### Remove All (⚠️ Destructive)

```bash
# Stop and remove everything
docker-compose down

# Remove data volumes
docker-compose down -v

# Remove images
docker image rm finai-v1.2_web postgres:15-alpine redis:7-alpine nginx:alpine

# Remove unused resources
docker system prune
```

---

## Further Reading

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Guide](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [Nginx Configuration](https://nginx.org/en/docs/)

---

**Last Updated**: March 6, 2026
**FinAI Version**: 1.2
