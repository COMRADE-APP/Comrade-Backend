#!/bin/bash
# Database Reset Script for Comrade Backend

echo "=========================================="
echo "Database Reset Script"
echo "=========================================="
echo ""

# Step 1: Check if Django server is running
echo "Step 1: Checking for running Django server..."
if pgrep -f "manage.py runserver" > /dev/null; then
    echo "⚠️  WARNING: Django server is running!"
    echo "Please stop the Django server (Ctrl+C in the terminal running it)"
    echo "Then run this script again."
    exit 1
fi

# Step 2: Backup existing database
echo "Step 2: Creating backup of existing database..."
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 "db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup created"
else
    echo "ℹ️  No existing database found"
fi

# Step 3: Delete database
echo "Step 3: Deleting database..."
rm -f db.sqlite3
echo "✅ Database deleted"

# Step 4: Run migrations
echo "Step 4: Running fresh migrations..."
source myenv/Scripts/activate
python manage.py makemigrations
python manage.py migrate
echo "✅ Migrations complete"

# Step 5: Create superuser (optional)
echo ""
echo "=========================================="
echo "Database reset complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Create a superuser: python manage.py createsuperuser"
echo "2. Start the server: python manage.py runserver"
