#!/bin/bash

# 🔍 Database Investigation Script
# Analyzes current autonomous agent database state and schema

echo "🔍 Investigating Autonomous Agent Database..."
echo "=============================================="

# Check if containers are running
echo "📊 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(postgres|autonomous)" || echo "No relevant containers found"
echo ""

# Check PostgreSQL container specifically
if docker ps | grep -q "autonomous_postgres_bridge"; then
    echo "✅ PostgreSQL container is running"
    
    # Check database connectivity
    echo "🔗 Testing database connectivity..."
    if docker exec autonomous_postgres_bridge pg_isready -U postgres -d autonomous_agent >/dev/null 2>&1; then
        echo "✅ Database is accepting connections"
        
        # List all tables
        echo ""
        echo "📋 Current Database Tables:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "\dt" 2>/dev/null || echo "No tables found or connection failed"
        
        # Check for ElizaOS specific tables
        echo ""
        echo "🔍 ElizaOS Framework Tables:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;" 2>/dev/null || echo "Could not query table information"
        
        # Check for any data in key tables
        echo ""
        echo "📊 Data Analysis:"
        
        # Check memories table (common in ElizaOS)
        echo "Memory entries:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT COUNT(*) as memory_count FROM memories;" 2>/dev/null || echo "No memories table found"
        
        # Check relationships table
        echo "Relationship entries:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT COUNT(*) as relationship_count FROM relationships;" 2>/dev/null || echo "No relationships table found"
        
        # Check goals table
        echo "Goal entries:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT COUNT(*) as goal_count FROM goals;" 2>/dev/null || echo "No goals table found"
        
        # Check rooms table
        echo "Room entries:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT COUNT(*) as room_count FROM rooms;" 2>/dev/null || echo "No rooms table found"
        
        # Check participants table
        echo "Participant entries:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT COUNT(*) as participant_count FROM participants;" 2>/dev/null || echo "No participants table found"
        
        # Sample recent memories if they exist
        echo ""
        echo "📝 Recent Memory Samples (last 5):"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT id, \"userId\", \"agentId\", \"createdAt\", 
               LEFT(content::text, 100) as content_preview
        FROM memories 
        ORDER BY \"createdAt\" DESC 
        LIMIT 5;" 2>/dev/null || echo "No memories table or data found"
        
        # Check database size
        echo ""
        echo "💾 Database Size Information:"
        docker exec autonomous_postgres_bridge psql -U postgres -d autonomous_agent -c "
        SELECT 
            schemaname,
            tablename,
            attname,
            n_distinct,
            correlation
        FROM pg_stats 
        WHERE schemaname = 'public'
        LIMIT 10;" 2>/dev/null || echo "Could not retrieve database statistics"
        
    else
        echo "❌ Database is not accepting connections"
    fi
    
else
    echo "❌ PostgreSQL container is not running"
    echo "Starting containers..."
    docker-compose -f docker-compose.bridge.yml up postgres -d 2>/dev/null || echo "Failed to start PostgreSQL"
fi

echo ""
echo "🔍 Investigation Complete!"
echo "==========================" 