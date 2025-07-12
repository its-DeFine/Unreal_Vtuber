#!/usr/bin/env python3
"""
Display Semantic Graph Structure
Shows the graph relationships in terminal
"""

import json

def display_semantic_graph():
    """Display the semantic graph structure"""
    
    # Load the D3.js data
    with open("semantic_graph_d3.json", "r") as f:
        data = json.load(f)
    
    print("🌐 SEMANTIC GRAPH STRUCTURE")
    print("=" * 70)
    
    # Create node lookup
    nodes = {n['id']: n['label'] for n in data['nodes']}
    
    # Group nodes by context
    contexts = {}
    for node in data['nodes']:
        ctx = node['group']
        if ctx not in contexts:
            contexts[ctx] = []
        contexts[ctx].append(node['label'])
    
    print("\n📊 NODES BY CONTEXT:")
    for ctx, node_list in sorted(contexts.items()):
        print(f"\n🔹 {ctx} ({len(node_list)} nodes):")
        for node in node_list:
            print(f"   • {node}")
    
    print("\n\n🔗 RELATIONSHIPS:")
    print("-" * 70)
    
    # Display relationships
    for link in data['links']:
        source_label = nodes[link['source']]
        target_label = nodes[link['target']]
        rel_type = link['type']
        
        # Format the output
        if len(source_label) > 30:
            source_label = source_label[:27] + "..."
        if len(target_label) > 30:
            target_label = target_label[:27] + "..."
        
        print(f"{source_label:35} --[{rel_type:12}]--> {target_label}")
    
    print("\n" + "=" * 70)
    print("📈 GRAPH FLOW:")
    print("\n1. S2 Analysis Phase:")
    print("   Market Analysis → Tool Execution → Trading Signal")
    
    print("\n2. Communication Phase:")
    print("   Trading Signal → S2→S1 Message → S1 Speech → S1 Confirmation")
    
    print("\n3. Execution Phase:")
    print("   S1 Confirmation → Trade Execution → Portfolio Update")
    
    print("\n4. Stimuli Processing:")
    print("   User Query → Route to S2 → Agent Collaboration → Consensus")
    
    print("\n5. System Monitoring:")
    print("   All components → System Health Check")

if __name__ == "__main__":
    display_semantic_graph()