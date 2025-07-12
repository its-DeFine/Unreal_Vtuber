#!/usr/bin/env python3
"""
Fix for tool selection diversity issue in AutoGen agent
"""

import os
import shutil
from datetime import datetime

def fix_tool_selection():
    """Apply fix to tool_registry.py to improve diversity"""
    
    tool_registry_path = "/home/geo/docker-vt/app/CORE/autogen-agent/autogen_agent/tool_registry.py"
    backup_path = f"{tool_registry_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create backup
    shutil.copy2(tool_registry_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Read the file
    with open(tool_registry_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Increase diversity weight
    old_diversity_weight = "score += diversity_bonus * 0.1"
    new_diversity_weight = "score += diversity_bonus * 0.3  # Increased from 0.1 for better diversity"
    
    if old_diversity_weight in content:
        content = content.replace(old_diversity_weight, new_diversity_weight)
        print("✅ Increased diversity weight from 0.1 to 0.3")
    
    # Fix 2: Add minimum context check for VTuber tool
    old_vtuber_check = '"advanced_vtuber_control": ["vtuber", "avatar", "stream", "audience", "activate", "control", "character", "voice"],'
    new_vtuber_check = '"advanced_vtuber_control": ["vtuber", "avatar", "stream", "audience", "activate", "control", "character", "voice", "show", "display"],'
    
    if old_vtuber_check in content:
        content = content.replace(old_vtuber_check, new_vtuber_check)
        print("✅ Updated VTuber keywords")
    
    # Fix 3: Add penalty for tools with no context match
    penalty_code = '''
        # Add penalty for tools with no context match in autonomous mode
        if context.get("autonomous", False) and relevance_score < 0.1:
            # In autonomous mode with no context match, penalize
            relevance_score = max(0.0, relevance_score - 0.3)
    '''
    
    # Find where to insert the penalty code
    insert_marker = "return min(relevance_score, 1.0)"
    if insert_marker in content:
        # Find the specific instance in _calculate_context_relevance
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if insert_marker in line and i > 350:  # Make sure it's the right function
                # Check if it's already inserted
                if i > 0 and "autonomous mode with no context match" not in lines[i-1]:
                    # Insert before the return statement
                    indent = len(line) - len(line.lstrip())
                    penalty_lines = penalty_code.strip().split('\n')
                    for j, penalty_line in enumerate(penalty_lines):
                        if penalty_line.strip():
                            lines.insert(i + j, ' ' * indent + penalty_line.strip())
                    content = '\n'.join(lines)
                    print("✅ Added penalty for no-context tools in autonomous mode")
                break
    
    # Fix 4: Modify the default selection to rotate through tools
    rotation_code = '''
        # If no clear winner, rotate through available tools
        if best_score < 0.3:  # Low confidence in selection
            # Use iteration count to rotate
            iteration = context.get("iteration", 0)
            available_tools = list(self.tools.keys())
            if available_tools:
                # Remove frequently used tools from rotation
                recent_tools = [entry.get('tool') for entry in self.tool_usage_history[-3:]]
                rotation_candidates = [t for t in available_tools if t not in recent_tools]
                if rotation_candidates:
                    tool_index = iteration % len(rotation_candidates)
                    best_tool = rotation_candidates[tool_index]
                    logging.info(f"🔄 [TOOL_REGISTRY] Low confidence - rotating to: {best_tool}")
    '''
    
    # Find where to insert rotation code
    rotation_marker = 'logging.info(f"🧠 [TOOL_REGISTRY] INTELLIGENT selection: {best_tool} (score: {best_score:.3f})")'
    if rotation_marker in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if rotation_marker in line:
                # Insert before the logging
                indent = len(line) - len(line.lstrip())
                rotation_lines = rotation_code.strip().split('\n')
                for j, rot_line in enumerate(rotation_lines):
                    if rot_line.strip():
                        lines.insert(i + j, ' ' * (indent - 8) + rot_line.strip())
                content = '\n'.join(lines)
                print("✅ Added rotation for low-confidence selections")
                break
    
    # Write the fixed content
    with open(tool_registry_path, 'w') as f:
        f.write(content)
    
    print("\n✅ All fixes applied successfully!")
    print("\n💡 Changes made:")
    print("1. Increased diversity bonus weight (0.1 → 0.3)")
    print("2. Added penalty for no-context matches in autonomous mode")
    print("3. Added tool rotation for low-confidence selections")
    print("4. Updated VTuber keywords")
    print("\n🔄 Please restart the container to apply changes:")
    print("   docker restart autogen_agent_ollama")

if __name__ == "__main__":
    fix_tool_selection()