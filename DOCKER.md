# Docker Deployment Guide for Splita Backend

This guide covers how to deploy the Splita Backend using Docker and Docker Compose for both development and production environments.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

## Quick Start (Development)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd splita-be
```

### 2. Environment Configuration

Copy the Docker environment file:
```bash
cp env.docker .env
```

Edit `.env` file if needed (the defaults work for development).

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Application

- **API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/
- **Database**: localhost:5432
- **Redis**: localhost:6379

### 5. Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

## Production Deployment

### 1. Environment Setup

Copy the production environment template:
```bash
cp env.production .env
```

Edit `.env` with your production values:
- Set `DEBUG=False`
- Use strong `SECRET_KEY` and `JWT_SECRET_KEY`
- Configure your domain in `ALLOWED_HOSTS`
- Set secure database credentials
- Configure Firebase and email settings

### 2. SSL Certificates

For HTTPS in production, place your SSL certificates in `docker/ssl/`:
```bash
mkdir -p docker/ssl
# Copy your certificates
cp your-cert.pem docker/ssl/cert.pem
cp your-key.pem docker/ssl/key.pem
```

### 3. Deploy with Production Compose

```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Docker Services

### Core Services

| Service | Description | Port | Health Check |
|---------|-------------|------|--------------|
| `web` | Django application | 8000 | `/admin/` |
| `db` | PostgreSQL database | 5432 | `pg_isready` |
| `redis` | Redis cache/broker | 6379 | `redis-cli ping` |
| `celery` | Background worker | - | - |
| `celery-beat` | Task scheduler | - | - |
| `nginx` | Reverse proxy | 80/443 | - |

### Service Dependencies

```
nginx → web → db, redis
celery → db, redis, web
celery-beat → db, redis, web
```

## Docker Commands

### Development Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild services
docker-compose build

# View logs
docker-compose logs -f [service_name]

# Execute commands in containers
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
docker-compose exec db psql -U postgres -d splita_db

# Scale services
docker-compose up -d --scale celery=3
```

### Production Commands

```bash
# Deploy production
docker-compose -f docker-compose.prod.yml up -d

# Update application
docker-compose -f docker-compose.prod.yml build web
docker-compose -f docker-compose.prod.yml up -d web

# Backup database
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres splita_db > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres splita_db < backup.sql
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-secret-key` |
| `DB_NAME` | Database name | `splita_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `secure-password` |
| `FIREBASE_SERVER_KEY` | Firebase server key | `your-firebase-key` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |

## Volumes and Data Persistence

### Named Volumes

- `postgres_data`: Database files
- `redis_data`: Redis persistence
- `static_volume`: Django static files
- `media_volume`: User uploaded files

### Backup Volumes

```bash
# Backup volumes
docker run --rm -v splita-be_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v splita-be_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 web

# Follow logs with timestamps
docker-compose logs -f -t web
```

### Health Checks

```bash
# Check container health
docker-compose ps

# Detailed health status
docker inspect splita_web --format='{{.State.Health.Status}}'

# Manual health check
curl -f http://localhost:8000/health/ || echo "Health check failed"
```

## Performance Optimization

### Production Optimizations

1. **Multi-stage builds**: Reduces image size
2. **Non-root user**: Security best practice
3. **Gunicorn**: Production WSGI server
4. **Nginx**: Static file serving and load balancing
5. **Health checks**: Container monitoring
6. **Resource limits**: Memory and CPU constraints

### Resource Limits (Production)

Add to your production compose file:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

## Security Considerations

### Development Security

- Default passwords (change for production)
- Debug mode enabled
- No SSL/HTTPS
- Permissive CORS settings

### Production Security

- Strong passwords and secrets
- SSL/HTTPS enabled
- Security headers configured
- Rate limiting enabled
- Non-root container user
- Minimal attack surface

### Security Checklist

- [ ] Change default passwords
- [ ] Use environment variables for secrets
- [ ] Enable SSL/HTTPS
- [ ] Configure security headers
- [ ] Set up rate limiting
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```bash
# Check database status
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec web python manage.py dbshell
```

#### 2. Redis Connection Error

```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### 3. Permission Errors

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Rebuild with correct permissions
docker-compose build --no-cache
```

#### 4. Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000

# Stop conflicting services
sudo systemctl stop apache2  # or nginx
```

#### 5. Out of Disk Space

```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune

# Check disk usage
df -h
docker system df
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set debug environment
echo "DEBUG=True" >> .env

# Restart services
docker-compose restart web

# View detailed logs
docker-compose logs -f web
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Update images
docker-compose pull

# Clean up unused resources
docker system prune

# Backup database
docker-compose exec db pg_dump -U postgres splita_db > backup_$(date +%Y%m%d).sql

# Update application
git pull
docker-compose build
docker-compose up -d
```

### Database Maintenance

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Clear cache
docker-compose exec web python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## Development Workflow

### Local Development with Docker

```bash
# Start development environment
docker-compose up -d

# Make code changes (files are mounted as volumes)

# Run tests
docker-compose exec web python manage.py test

# Run migrations after model changes
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Access Django shell
docker-compose exec web python manage.py shell

# Install new packages
# 1. Add to requirements.txt
# 2. Rebuild container
docker-compose build web
docker-compose up -d web
```

### Testing

```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific test
docker-compose exec web python manage.py test accounts.tests.test_models

# Run with coverage
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
```

## Scaling

### Horizontal Scaling

```bash
# Scale web workers
docker-compose up -d --scale web=3

# Scale Celery workers
docker-compose up -d --scale celery=5

# Use load balancer (nginx handles this automatically)
```

### Vertical Scaling

Adjust resource limits in docker-compose files:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

## Migration from Non-Docker Setup

### 1. Export Data

```bash
# Export database
python manage.py dumpdata > data.json

# Copy media files
cp -r media/ docker-media/
```

### 2. Import to Docker

```bash
# Start Docker services
docker-compose up -d

# Import data
docker-compose exec web python manage.py loaddata data.json

# Copy media files
docker cp docker-media/. splita_web:/app/media/
```

## Support

For issues and questions:

1. Check this documentation
2. Review Docker logs: `docker-compose logs`
3. Check container status: `docker-compose ps`
4. Create an issue in the repository

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
- [Redis Docker Hub](https://hub.docker.com/_/redis) 