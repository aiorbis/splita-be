#!/bin/bash

# Splita Backend Docker Setup Script
# This script helps with common Docker operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Function to setup environment
setup_env() {
    print_status "Setting up environment..."
    
    if [ ! -f .env ]; then
        if [ "$1" = "production" ]; then
            cp env.production .env
            print_warning "Production environment template copied to .env"
            print_warning "Please edit .env with your production settings before continuing"
        else
            cp env.docker .env
            print_success "Development environment copied to .env"
        fi
    else
        print_warning ".env file already exists, skipping..."
    fi
}

# Function to start development environment
start_dev() {
    print_status "Starting development environment..."
    
    setup_env "development"
    
    print_status "Building and starting services..."
    docker-compose up -d
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    print_status "Running database migrations..."
    docker-compose exec web python manage.py migrate
    
    print_status "Creating notification templates..."
    docker-compose exec web python manage.py create_notification_templates
    
    print_success "Development environment is ready!"
    print_status "Access points:"
    echo "  - API: http://localhost:8000/api/"
    echo "  - Admin: http://localhost:8000/admin/"
    echo "  - Database: localhost:5432"
    echo "  - Redis: localhost:6379"
    
    read -p "Do you want to create a superuser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose exec web python manage.py createsuperuser
    fi
}

# Function to start production environment
start_prod() {
    print_status "Starting production environment..."
    
    setup_env "production"
    
    if [ ! -f .env ]; then
        print_error "Please configure .env file with production settings"
        exit 1
    fi
    
    # Check if SSL certificates exist
    if [ ! -d "docker/ssl" ]; then
        print_warning "SSL certificates not found in docker/ssl/"
        print_warning "Creating self-signed certificates for testing..."
        mkdir -p docker/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout docker/ssl/key.pem \
            -out docker/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        print_warning "Self-signed certificates created. Replace with real certificates for production."
    fi
    
    print_status "Building and starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_status "Waiting for services to be ready..."
    sleep 15
    
    print_status "Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
    
    print_status "Creating notification templates..."
    docker-compose -f docker-compose.prod.yml exec web python manage.py create_notification_templates
    
    print_status "Collecting static files..."
    docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
    
    print_success "Production environment is ready!"
    print_status "Access points:"
    echo "  - HTTPS: https://localhost/"
    echo "  - HTTP: http://localhost/ (redirects to HTTPS)"
    
    read -p "Do you want to create a superuser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi
    
    print_success "Services stopped"
}

# Function to view logs
view_logs() {
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml logs -f "${2:-}"
    else
        docker-compose logs -f "${2:-}"
    fi
}

# Function to backup database
backup_db() {
    print_status "Creating database backup..."
    
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres splita_db > "$BACKUP_FILE"
    else
        docker-compose exec db pg_dump -U postgres splita_db > "$BACKUP_FILE"
    fi
    
    print_success "Database backup created: $BACKUP_FILE"
}

# Function to restore database
restore_db() {
    if [ -z "$2" ]; then
        print_error "Please provide backup file path"
        exit 1
    fi
    
    if [ ! -f "$2" ]; then
        print_error "Backup file not found: $2"
        exit 1
    fi
    
    print_status "Restoring database from: $2"
    
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres splita_db < "$2"
    else
        docker-compose exec -T db psql -U postgres splita_db < "$2"
    fi
    
    print_success "Database restored successfully"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml exec web python manage.py test
    else
        docker-compose exec web python manage.py test
    fi
}

# Function to clean up Docker resources
cleanup() {
    print_status "Cleaning up Docker resources..."
    
    docker system prune -f
    docker volume prune -f
    
    print_success "Docker cleanup completed"
}

# Function to show status
show_status() {
    print_status "Service status:"
    
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.prod.yml ps
    else
        docker-compose ps
    fi
}

# Function to show help
show_help() {
    echo "Splita Backend Docker Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  dev                 Start development environment"
    echo "  prod                Start production environment"
    echo "  stop [prod]         Stop services (add 'prod' for production)"
    echo "  logs [prod] [service] View logs (add 'prod' for production, optional service name)"
    echo "  status [prod]       Show service status"
    echo "  backup [prod]       Backup database"
    echo "  restore [prod] <file> Restore database from backup file"
    echo "  test [prod]         Run tests"
    echo "  cleanup             Clean up Docker resources"
    echo "  help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev              # Start development environment"
    echo "  $0 prod             # Start production environment"
    echo "  $0 logs             # View development logs"
    echo "  $0 logs prod web    # View production web service logs"
    echo "  $0 backup           # Backup development database"
    echo "  $0 restore prod backup.sql # Restore production database"
}

# Main script logic
case "${1:-help}" in
    "dev")
        check_docker
        start_dev
        ;;
    "prod")
        check_docker
        start_prod
        ;;
    "stop")
        stop_services "$2"
        ;;
    "logs")
        view_logs "$2" "$3"
        ;;
    "status")
        show_status "$2"
        ;;
    "backup")
        backup_db "$2"
        ;;
    "restore")
        restore_db "$2" "$3"
        ;;
    "test")
        run_tests "$2"
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        show_help
        ;;
esac 