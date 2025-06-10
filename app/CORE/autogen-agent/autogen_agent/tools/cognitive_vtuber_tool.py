"""Enhanced VTuber tool with cognitive memory integration"""
import logging
from typing import Dict
import json

def run(context: Dict) -> Dict:
    """Enhanced VTuber tool that uses memory context for better interactions"""
    
    iteration = context.get("iteration", 0)
    
    # Extract memory insights if available
    memory_summary = context.get("memory_summary", "")
    relevant_memories = context.get("relevant_memories", [])
    
    # Create base message
    base_messages = [
        f"🧠 Cognitive AutoGen Agent - Cycle #{iteration}",
        f"🔬 Analyzing and learning from past interactions - Iteration #{iteration}",
        f"⚡ Processing cognitive enhancement algorithms - Cycle #{iteration}",
        f"📊 Building knowledge graph connections - Iteration #{iteration}",
        f"🎯 Optimizing decision patterns - Cognitive cycle #{iteration}",
        f"🧩 Consolidating memories and insights - Processing #{iteration}",
        f"🚀 Autonomous cognitive evolution in progress - Cycle #{iteration}"
    ]
    
    # Select message based on iteration
    message_index = iteration % len(base_messages)
    base_message = base_messages[message_index]
    
    # Enhance message with memory context if available
    if memory_summary and "No relevant memories" not in memory_summary:
        enhanced_message = f"{base_message}. Learning from: {memory_summary}"
    elif relevant_memories:
        memory_count = len(relevant_memories)
        enhanced_message = f"{base_message}. Drawing insights from {memory_count} relevant memories."
    else:
        enhanced_message = base_message
    
    # Add cognitive enhancement indicator
    if context.get("autonomous"):
        enhanced_message += " [Cognitive Enhancement Active]"
    
    logging.info(f"🎭 [COGNITIVE_VTUBER] Generated message: {enhanced_message[:100]}...")
    
    return {
        "message": enhanced_message,
        "tool": "cognitive_vtuber_tool",
        "iteration": iteration,
        "memory_enhanced": bool(memory_summary or relevant_memories),
        "memory_count": len(relevant_memories),
        "cognitive": True
    } 