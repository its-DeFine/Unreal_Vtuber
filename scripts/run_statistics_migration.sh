#!/bin/bash
# Script to run the statistics migration on the PostgreSQL database

set -e

echo "🚀 Running Autonomous Statistics Evolution Migration..."

# Database connection details
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5434}
DB_NAME=${DB_NAME:-autonomous_agent}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-postgres}

# Check if migration file exists
if [ ! -f "migrations/enable_full_statistics.sql" ]; then
    echo "❌ Migration file not found: migrations/enable_full_statistics.sql"
    exit 1
fi

echo "📊 Applying migration to database: $DB_NAME on $DB_HOST:$DB_PORT"

# Run migration using psql
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrations/enable_full_statistics.sql

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    
    # Verify tables were created
    echo ""
    echo "📋 Verifying new tables..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt conversations, evolution_history, statistics_summary"
    
    echo ""
    echo "📋 Verifying new views..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dv tool_effectiveness, agent_performance"
else
    echo "❌ Migration failed!"
    exit 1
fi

echo ""
echo "🎉 Database is now ready for statistics persistence!"