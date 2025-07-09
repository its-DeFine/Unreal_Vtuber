#!/usr/bin/env python3
"""
Demo Neo4j Semantic Graph with Mock Data
Generates a visualization without requiring full container setup
"""

import json
import time
from datetime import datetime
import networkx as nx
from pyvis.network import Network
import random

def create_mock_semantic_graph():
    """Create a mock semantic graph with S1/S2 communication data"""
    
    # Create directed graph
    G = nx.DiGraph()
    
    # Define nodes with their contexts
    nodes = [
        # S2 Analysis Nodes
        ("s2_market_analysis", "S2: Bitcoin market analysis", "trading_finance", "#e377c2"),
        ("s2_tool_scanner", "Tool: crypto_market_scanner", "tool_executions", "#d62728"),
        ("s2_trading_signal", "S2: Buy signal BTC @ $48k", "trading_finance", "#e377c2"),
        
        # S2 to S1 Communication
        ("s2_to_s1_msg1", "S2→S1: Inform user about BTC opportunity", "s2_to_s1_messages", "#ff7f0e"),
        ("s2_to_s1_msg2", "S2→S1: Execute buy order confirmation", "s2_to_s1_messages", "#ff7f0e"),
        
        # S1 Responses
        ("s1_speech1", "S1: 'Great Bitcoin buying opportunity!'", "s1_to_s2_feedback", "#2ca02c"),
        ("s1_confirm", "S1→S2: User informed successfully", "s1_to_s2_feedback", "#2ca02c"),
        
        # Trading Execution
        ("trade_execute", "Trade: BUY 0.5 BTC @ $48,200", "trading_finance", "#e377c2"),
        ("portfolio_update", "Portfolio: 1.5 BTC, 5 ETH, $25k USD", "trading_finance", "#e377c2"),
        
        # Stimuli Processing
        ("stimuli_1", "Stimuli: 'What's my portfolio value?'", "stimuli_context", "#9467bd"),
        ("stimuli_route", "Route to S2 portfolio manager", "stimuli_context", "#9467bd"),
        
        # Agent State
        ("agent_collab", "3 S2 agents collaborated", "agent_state", "#8c564b"),
        ("consensus", "Consensus: Buy recommendation", "agent_state", "#8c564b"),
        
        # System Events
        ("system_health", "All services operational", "system_events", "#7f7f7f"),
    ]
    
    # Add nodes to graph
    for node_id, label, context, color in nodes:
        G.add_node(node_id, 
                   label=label, 
                   title=f"{label}\nContext: {context}\nTime: {datetime.now().strftime('%H:%M:%S')}",
                   group=context,
                   color=color,
                   size=25)
    
    # Define relationships
    edges = [
        # Analysis flow
        ("s2_market_analysis", "s2_tool_scanner", "TRIGGERS"),
        ("s2_tool_scanner", "s2_trading_signal", "PRODUCES"),
        
        # Communication flow
        ("s2_trading_signal", "s2_to_s1_msg1", "INITIATES"),
        ("s2_to_s1_msg1", "s1_speech1", "CAUSES"),
        ("s1_speech1", "s1_confirm", "FOLLOWED_BY"),
        ("s1_confirm", "s2_to_s1_msg2", "TRIGGERS"),
        
        # Trading flow
        ("s2_to_s1_msg2", "trade_execute", "EXECUTES"),
        ("trade_execute", "portfolio_update", "UPDATES"),
        
        # Stimuli flow
        ("stimuli_1", "stimuli_route", "ROUTES_TO"),
        ("stimuli_route", "agent_collab", "ACTIVATES"),
        ("agent_collab", "consensus", "REACHES"),
        
        # System monitoring
        ("portfolio_update", "system_health", "MONITORED_BY"),
        ("consensus", "system_health", "MONITORED_BY"),
    ]
    
    # Add edges to graph
    for source, target, rel_type in edges:
        G.add_edge(source, target, title=rel_type, label=rel_type)
    
    return G

def generate_pyvis_visualization(G, output_file="semantic_graph_demo.html"):
    """Generate interactive PyVis visualization"""
    
    # Create PyVis network
    net = Network(height="750px", width="100%", directed=True, notebook=False)
    
    # Configure physics for better layout
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.01,
        damping=0.09
    )
    
    # Add nodes from NetworkX graph
    for node, attrs in G.nodes(data=True):
        net.add_node(
            node,
            label=attrs.get('label', node),
            title=attrs.get('title', attrs.get('label', node)),
            color=attrs.get('color', '#17a2b8'),
            size=attrs.get('size', 25)
        )
    
    # Add edges
    for source, target, attrs in G.edges(data=True):
        net.add_edge(
            source,
            target,
            title=attrs.get('title', attrs.get('label', '')),
            arrows="to",
            color="#666"
        )
    
    # Add custom options
    net.set_options("""
    var options = {
        "nodes": {
            "font": {
                "size": 14,
                "color": "white",
                "strokeWidth": 2,
                "strokeColor": "black"
            },
            "borderWidth": 2,
            "shadow": true
        },
        "edges": {
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.8
                }
            },
            "color": {
                "inherit": false
            },
            "font": {
                "size": 10,
                "color": "#999",
                "strokeWidth": 0
            },
            "smooth": {
                "type": "continuous"
            }
        },
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 150,
                "springConstant": 0.01,
                "damping": 0.09,
                "avoidOverlap": 0.5
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "hideEdgesOnDrag": true
        }
    }
    """)
    
    # Generate HTML
    net.save_graph(output_file)
    print(f"✅ Visualization saved to: {output_file}")
    
    return output_file

def export_d3_format(G):
    """Export graph in D3.js format"""
    
    nodes = []
    for node, attrs in G.nodes(data=True):
        nodes.append({
            "id": node,
            "label": attrs.get('label', node),
            "group": attrs.get('group', 'default'),
            "title": attrs.get('title', ''),
            "metadata": {
                "timestamp": time.time(),
                "context": attrs.get('group', 'default')
            }
        })
    
    links = []
    for source, target, attrs in G.edges(data=True):
        links.append({
            "source": source,
            "target": target,
            "type": attrs.get('label', 'RELATED'),
            "value": 1
        })
    
    d3_data = {
        "nodes": nodes,
        "links": links
    }
    
    with open("semantic_graph_d3.json", "w") as f:
        json.dump(d3_data, f, indent=2)
    
    print(f"✅ D3.js data exported to: semantic_graph_d3.json")
    print(f"   - Nodes: {len(nodes)}")
    print(f"   - Links: {len(links)}")
    
    return d3_data

def print_graph_stats(G):
    """Print graph statistics"""
    print("\n📊 GRAPH STATISTICS:")
    print(f"   - Total Nodes: {G.number_of_nodes()}")
    print(f"   - Total Edges: {G.number_of_edges()}")
    print(f"   - Density: {nx.density(G):.3f}")
    
    # Context distribution
    contexts = {}
    for node, attrs in G.nodes(data=True):
        ctx = attrs.get('group', 'unknown')
        contexts[ctx] = contexts.get(ctx, 0) + 1
    
    print("\n   Context Distribution:")
    for ctx, count in sorted(contexts.items()):
        print(f"     • {ctx}: {count} nodes")
    
    # Node degrees
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    print("\n   Most Connected Nodes:")
    sorted_nodes = sorted(G.nodes(), key=lambda n: in_degrees[n] + out_degrees[n], reverse=True)[:5]
    for node in sorted_nodes:
        label = G.nodes[node].get('label', node)
        print(f"     • {label}: {in_degrees[node]} in, {out_degrees[node]} out")

def main():
    """Generate demo semantic graph"""
    print("🚀 NEO4J SEMANTIC GRAPH DEMO")
    print("=" * 50)
    
    # Create mock graph
    print("\n1️⃣ Creating mock semantic graph...")
    G = create_mock_semantic_graph()
    
    # Print statistics
    print_graph_stats(G)
    
    # Generate visualizations
    print("\n2️⃣ Generating visualizations...")
    
    # PyVis interactive HTML
    html_file = generate_pyvis_visualization(G)
    
    # D3.js export
    d3_data = export_d3_format(G)
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ DEMO COMPLETE!")
    print("\n📁 Generated Files:")
    print(f"   - Interactive HTML: {html_file}")
    print(f"   - D3.js JSON: semantic_graph_d3.json")
    
    print("\n🌐 The semantic graph shows:")
    print("   - S2 market analysis → tool execution → trading signals")
    print("   - S2→S1 communication flow for user notifications")
    print("   - S1→S2 feedback and confirmations")
    print("   - Trading execution and portfolio updates")
    print("   - Stimuli routing and agent collaboration")
    print("   - Complete system state monitoring")
    
    print("\n💡 To view the graph:")
    print(f"   1. Open {html_file} in a web browser")
    print("   2. Drag nodes to rearrange")
    print("   3. Hover over nodes/edges for details")
    print("   4. Use mouse wheel to zoom")

if __name__ == "__main__":
    main()