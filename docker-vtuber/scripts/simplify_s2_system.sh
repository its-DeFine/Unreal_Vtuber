#!/bin/bash
# Simplify S2 System - Remove complex features and keep only 3 teams

echo "🧹 Simplifying S2 System..."

# Navigate to the autogen directory
cd /home/geo/directories/autonomy/docker-vtuber/app/CORE/autogen-agent

# Remove complex files
echo "❌ Removing evolution system..."
rm -rf autogen_agent/evolution/

echo "❌ Removing complex services..."
rm -f autogen_agent/services/evolution_service.py
rm -f autogen_agent/services/goal_management_service.py
rm -f autogen_agent/services/pattern_storage_service.py

echo "❌ Removing complex tools..."
rm -f autogen_agent/tools/system/core_evolution_tool.py
rm -f autogen_agent/tools/system/goal_management_tools.py

echo "❌ Removing teachable agents..."
rm -f autogen_agent/core/teachable_agents.py

echo "❌ Removing complex test files..."
rm -rf /home/geo/directories/autonomy/docker-vtuber/tests/core/autogen/test_darwin*
rm -rf /home/geo/directories/autonomy/docker-vtuber/tests/core/autogen/test_teachable*
rm -rf /home/geo/directories/autonomy/docker-vtuber/tests/decide/integration/test_goal*
rm -rf /home/geo/directories/autonomy/docker-vtuber/tests/decide/integration/final_goal*

echo "✅ Cleanup complete!"

# Update imports in __init__ files
echo "📝 Updating imports..."

# Remove evolution imports from services init
sed -i '/evolution_service/d' autogen_agent/services/__init__.py 2>/dev/null || true
sed -i '/goal_management_service/d' autogen_agent/services/__init__.py 2>/dev/null || true
sed -i '/pattern_storage_service/d' autogen_agent/services/__init__.py 2>/dev/null || true

echo "✅ Simplification complete!"
echo ""
echo "Next steps:"
echo "1. Use simplified_main.py as the main entry point"
echo "2. Rebuild the Docker container"
echo "3. Test with the 3 specialized teams only"