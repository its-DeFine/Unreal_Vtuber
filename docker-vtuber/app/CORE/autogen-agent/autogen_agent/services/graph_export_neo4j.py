"""
Graph Export Service for Neo4j
Exports semantic graphs in various formats for visualization
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from io import StringIO

import networkx as nx
from pyvis.network import Network

from .neo4j_semantic_storage import (
    Neo4jSemanticStorage,
    SemanticContext,
    get_neo4j_storage
)

logger = logging.getLogger(__name__)


class GraphExportService:
    """Service for exporting Neo4j graphs in various formats"""
    
    def __init__(self):
        self.storage = get_neo4j_storage()
        self.cache = {}
        self.cache_timestamp = None
        self.cache_duration = 300  # 5 minutes
        logger.info("📊 [GRAPH_EXPORT] Initialized export service")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.cache_timestamp:
            return False
        return (datetime.now().timestamp() - self.cache_timestamp) < self.cache_duration
    
    async def get_graph_data(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Get graph data from Neo4j"""
        cache_key = f"graph_{context_filter.value if context_filter else 'all'}"
        
        if self._is_cache_valid() and cache_key in self.cache:
            logger.info("📦 [GRAPH_EXPORT] Using cached graph data")
            return self.cache[cache_key]
        
        # Get fresh data from Neo4j
        graph_data = await self.storage.get_graph_data(context_filter)
        
        # Update cache
        self.cache[cache_key] = graph_data
        self.cache_timestamp = datetime.now().timestamp()
        
        return graph_data
    
    async def export_d3js(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Export graph in D3.js format"""
        graph_data = await self.get_graph_data(context_filter)
        
        # D3.js format with proper node and link structure
        d3_data = {
            "nodes": [
                {
                    "id": node["id"],
                    "label": node["label"],
                    "title": node["title"],
                    "group": node["group"],
                    "type": node["type"],
                    "metadata": node["metadata"]
                }
                for node in graph_data["nodes"]
            ],
            "links": [
                {
                    "source": link["source"],
                    "target": link["target"],
                    "type": link["type"],
                    "value": 1
                }
                for link in graph_data["links"]
            ]
        }
        
        return {
            "format": "d3js",
            "data": d3_data,
            "nodes": len(d3_data["nodes"]),
            "edges": len(d3_data["links"]),
            "timestamp": datetime.now().isoformat()
        }
    
    async def export_networkx(self, context_filter: Optional[SemanticContext] = None) -> nx.Graph:
        """Export as NetworkX graph"""
        graph_data = await self.get_graph_data(context_filter)
        
        G = nx.DiGraph()
        
        # Add nodes
        for node in graph_data["nodes"]:
            G.add_node(
                node["id"],
                label=node["label"],
                title=node["title"],
                group=node["group"],
                node_type=node["type"],
                **node["metadata"]
            )
        
        # Add edges
        for link in graph_data["links"]:
            G.add_edge(
                link["source"],
                link["target"],
                rel_type=link["type"]
            )
        
        return G
    
    async def export_graphml(self, context_filter: Optional[SemanticContext] = None) -> str:
        """Export in GraphML format"""
        G = await self.export_networkx(context_filter)
        
        # Convert to GraphML
        output = StringIO()
        nx.write_graphml(G, output)
        graphml_str = output.getvalue()
        output.close()
        
        return {
            "format": "graphml",
            "data": graphml_str,
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def export_json_ld(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Export in JSON-LD format"""
        graph_data = await self.get_graph_data(context_filter)
        
        # Create JSON-LD structure
        json_ld = {
            "@context": {
                "semantic": "http://schema.org/",
                "nodes": "semantic:nodes",
                "relationships": "semantic:relationships",
                "content": "semantic:text",
                "context": "semantic:category",
                "timestamp": "semantic:dateCreated"
            },
            "@graph": []
        }
        
        # Add nodes
        for node in graph_data["nodes"]:
            json_ld["@graph"].append({
                "@id": f"node:{node['id']}",
                "@type": node["type"],
                "content": node["title"],
                "context": node["group"],
                "metadata": node["metadata"]
            })
        
        # Add relationships
        for link in graph_data["links"]:
            json_ld["@graph"].append({
                "@type": "Relationship",
                "source": f"node:{link['source']}",
                "target": f"node:{link['target']}",
                "relationType": link["type"]
            })
        
        return {
            "format": "json_ld",
            "data": json_ld,
            "nodes": len(graph_data["nodes"]),
            "edges": len(graph_data["links"]),
            "timestamp": datetime.now().isoformat()
        }
    
    async def export_cytoscape(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Export in Cytoscape format"""
        graph_data = await self.get_graph_data(context_filter)
        
        # Cytoscape format
        elements = []
        
        # Add nodes
        for node in graph_data["nodes"]:
            elements.append({
                "data": {
                    "id": node["id"],
                    "label": node["label"],
                    "group": node["group"],
                    "type": node["type"]
                }
            })
        
        # Add edges
        for link in graph_data["links"]:
            elements.append({
                "data": {
                    "id": f"{link['source']}-{link['target']}",
                    "source": link["source"],
                    "target": link["target"],
                    "type": link["type"]
                }
            })
        
        return {
            "format": "cytoscape",
            "data": {"elements": elements},
            "nodes": len(graph_data["nodes"]),
            "edges": len(graph_data["links"]),
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_pyvis_visualization(
        self, 
        context_filter: Optional[SemanticContext] = None,
        height: str = "750px",
        width: str = "100%"
    ) -> str:
        """Generate interactive PyVis visualization"""
        graph_data = await self.get_graph_data(context_filter)
        
        # Create PyVis network
        net = Network(height=height, width=width, directed=True)
        
        # Configure physics
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=100,
            spring_strength=0.01,
            damping=0.09
        )
        
        # Color mapping for contexts
        color_map = {
            "general_context": "#1f77b4",
            "s2_to_s1_messages": "#ff7f0e",
            "s1_to_s2_feedback": "#2ca02c",
            "tool_executions": "#d62728",
            "stimuli_context": "#9467bd",
            "agent_state": "#8c564b",
            "trading_finance": "#e377c2",
            "system_events": "#7f7f7f"
        }
        
        # Add nodes
        for node in graph_data["nodes"]:
            net.add_node(
                node["id"],
                label=node["label"],
                title=node["title"],
                color=color_map.get(node["group"], "#17a2b8"),
                size=25
            )
        
        # Add edges
        for link in graph_data["links"]:
            net.add_edge(
                link["source"],
                link["target"],
                title=link["type"],
                arrows="to"
            )
        
        # Generate HTML
        html = net.generate_html()
        
        return html
    
    async def get_graph_metrics(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """Get graph metrics and analysis"""
        G = await self.export_networkx(context_filter)
        
        metrics = {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": nx.density(G) if G.number_of_nodes() > 0 else 0,
            "components": nx.number_weakly_connected_components(G) if G.is_directed() else nx.number_connected_components(G)
        }
        
        if G.number_of_nodes() > 0:
            # Degree metrics
            degrees = dict(G.degree())
            metrics["average_degree"] = sum(degrees.values()) / len(degrees)
            metrics["max_degree"] = max(degrees.values()) if degrees else 0
            
            # Centrality metrics (for small graphs)
            if G.number_of_nodes() < 100:
                try:
                    metrics["betweenness_centrality"] = nx.betweenness_centrality(G)
                    metrics["closeness_centrality"] = nx.closeness_centrality(G)
                except:
                    pass
        
        # Context distribution
        context_dist = {}
        for node_id, data in G.nodes(data=True):
            context = data.get("group", "unknown")
            context_dist[context] = context_dist.get(context, 0) + 1
        metrics["context_distribution"] = context_dist
        
        return metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "graph_export_neo4j",
            "networkx_available": True,
            "pyvis_available": True,
            "neo4j_connected": self.storage.driver is not None,
            "cache_valid": self._is_cache_valid(),
            "supported_formats": [
                "graphml", "json_ld", "gexf", "d3js", 
                "cytoscape", "dot", "networkx"
            ]
        }


# Global instance
_export_service = None


def get_graph_export_service() -> GraphExportService:
    """Get or create global export service"""
    global _export_service
    if _export_service is None:
        _export_service = GraphExportService()
    return _export_service