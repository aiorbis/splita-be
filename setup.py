#!/usr/bin/env python3
"""
Setup script for Splita Backend
This script automates the database setup and initial configuration
"""

import os
import sys
import subprocess
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent / 'splita'
sys.path.insert(0, str(project_dir))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'splita.settings')

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"🔄 {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Starting Splita Backend Setup")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(project_dir)
    
    # Setup steps
    steps = [
        ("python3 manage.py makemigrations accounts", "Creating accounts migrations"),
        ("python3 manage.py makemigrations credit_cards", "Creating credit cards migrations"),
        ("python3 manage.py makemigrations loans", "Creating loans migrations"),
        ("python3 manage.py makemigrations dashboard", "Creating dashboard migrations"),
        ("python3 manage.py makemigrations notifications", "Creating notifications migrations"),
        ("python3 manage.py migrate", "Running database migrations"),
        ("python3 manage.py create_notification_templates", "Creating notification templates"),
    ]
    
    # Execute setup steps
    for command, description in steps:
        if not run_command(command, description):
            print(f"\n❌ Setup failed at: {description}")
            sys.exit(1)
    
    # Create superuser prompt
    print(f"\n{'='*50}")
    print("👤 Creating Superuser")
    print(f"{'='*50}")
    print("Please create a superuser account for admin access:")
    
    try:
        subprocess.run("python3 manage.py createsuperuser", shell=True, check=True)
        print("✅ Superuser created successfully")
    except subprocess.CalledProcessError:
        print("⚠️  Superuser creation skipped or failed")
    except KeyboardInterrupt:
        print("⚠️  Superuser creation cancelled")
    
    # Final success message
    print(f"\n{'='*60}")
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print(f"{'='*60}")
    print("\n📋 Next Steps:")
    print("1. Update your .env file with proper database and API keys")
    print("2. Start the development server: python manage.py runserver")
    print("3. (Optional) Start Celery worker: celery -A splita worker -l info")
    print("4. (Optional) Start Celery beat: celery -A splita beat -l info")
    print("\n🌐 API Documentation:")
    print("- Admin Panel: http://localhost:8000/admin/")
    print("- API Base URL: http://localhost:8000/api/")
    print("\n📚 Available API Endpoints:")
    print("- Authentication: /api/accounts/")
    print("- Credit Cards: /api/credit-cards/")
    print("- Loans: /api/loans/")
    print("- Dashboard: /api/dashboard/")
    print("- Notifications: /api/notifications/")

if __name__ == "__main__":
    main() 