"""
Graph Export Service for Cognee Knowledge Graphs

This service provides functionality to export and visualize the knowledge graphs
stored in Cognee. It supports multiple export formats and creates interactive
visualizations for understanding semantic relationships.

Key Features:
1. Export to multiple graph formats (GraphML, JSON-LD, GEXF, D3.js)
2. Generate interactive HTML visualizations using pyvis
3. Create NetworkX graphs for analysis
4. Support for subgraph extraction by context
5. Time-based snapshots of graph evolution
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("⚠️ [GRAPH_EXPORT] NetworkX not available - graph analysis features disabled")

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    logging.warning("⚠️ [GRAPH_EXPORT] PyVis not available - interactive visualization disabled")

from .scb_cognee_bridge import SemanticContext, get_scb_cognee_bridge
from .cognee_direct_service import get_cognee_direct_service
from .cognee_service import CogneeService


class ExportFormat(Enum):
    """Supported graph export formats"""
    GRAPHML = "graphml"          # Standard graph format
    JSON_LD = "json_ld"          # JSON Linked Data
    GEXF = "gexf"                # Gephi format
    D3JS = "d3js"                # D3.js compatible JSON
    CYTOSCAPE = "cytoscape"      # Cytoscape.js format
    DOT = "dot"                  # Graphviz DOT format
    NETWORKX = "networkx"        # NetworkX Python object


@dataclass
class GraphNode:
    """Represents a node in the knowledge graph"""
    id: str
    label: str
    context: str
    node_type: str = "entity"
    metadata: Dict[str, Any] = None
    timestamp: Optional[datetime] = None


@dataclass
class GraphEdge:
    """Represents an edge (relationship) in the knowledge graph"""
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    metadata: Dict[str, Any] = None


class GraphExportService:
    """
    Service for exporting and visualizing Cognee knowledge graphs
    """
    
    def __init__(self):
        """Initialize the graph export service"""
        self.cognee_direct = None
        self.cognee_service = None
        self.bridge = None
        
        # Graph cache
        self.graph_cache: Optional[nx.Graph] = None
        self.cache_timestamp: Optional[datetime] = None
        self.cache_duration = timedelta(minutes=5)
        
        logging.info("📊 [GRAPH_EXPORT] Graph Export Service initialized")
    
    async def initialize(self) -> bool:
        """Initialize service dependencies"""
        try:
            # Get Cognee services
            self.cognee_direct = await get_cognee_direct_service()
            self.bridge = await get_scb_cognee_bridge()
            
            if not self.cognee_direct and not self.cognee_service:
                logging.error("❌ [GRAPH_EXPORT] No Cognee service available")
                return False
            
            logging.info("✅ [GRAPH_EXPORT] Service initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Initialization error: {e}")
            return False
    
    async def extract_knowledge_graph(self, 
                                    context_filter: Optional[SemanticContext] = None,
                                    time_range: Optional[Tuple[datetime, datetime]] = None) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Extract knowledge graph data from Cognee
        
        Args:
            context_filter: Optional filter for specific semantic context
            time_range: Optional time range filter (start, end)
            
        Returns:
            Tuple of (nodes, edges)
        """
        nodes = []
        edges = []
        seen_nodes = set()
        
        try:
            # Search for all data in the specified context
            query = f"[{context_filter.value}]" if context_filter else ""
            
            # Get search results from Cognee
            if self.cognee_direct:
                results = await self.cognee_direct.search(query, limit=100)
            elif self.cognee_service:
                results = await self.cognee_service.search(query, search_type="GRAPH_COMPLETION", limit=100)
            else:
                return nodes, edges
            
            # Process results to extract nodes and relationships
            for i, result in enumerate(results):
                # Extract content and metadata
                if isinstance(result, dict):
                    content = result.get("content", str(result))
                    metadata = result.get("metadata", {})
                else:
                    content = str(result)
                    metadata = {}
                
                # Parse semantic context from content
                context = "general"
                if content.startswith("[") and "]" in content:
                    context_end = content.index("]")
                    context = content[1:context_end]
                    content = content[context_end + 1:].strip()
                
                # Create node
                node_id = f"node_{i}_{hash(content)}"
                node = GraphNode(
                    id=node_id,
                    label=content[:50] + "..." if len(content) > 50 else content,
                    context=context,
                    metadata=metadata
                )
                
                if node_id not in seen_nodes:
                    nodes.append(node)
                    seen_nodes.add(node_id)
                
                # Extract relationships from content
                if "Relations:" in content:
                    rel_start = content.index("Relations:") + 10
                    rel_section = content[rel_start:].split("|")[0].strip()
                    
                    for rel in rel_section.split(","):
                        rel = rel.strip()
                        if ":" in rel:
                            rel_type, target = rel.split(":", 1)
                            
                            # Create target node if not exists
                            target_id = f"node_{hash(target)}"
                            if target_id not in seen_nodes:
                                target_node = GraphNode(
                                    id=target_id,
                                    label=target.strip(),
                                    context=context,
                                    node_type="reference"
                                )
                                nodes.append(target_node)
                                seen_nodes.add(target_id)
                            
                            # Create edge
                            edge = GraphEdge(
                                source=node_id,
                                target=target_id,
                                relationship=rel_type.strip()
                            )
                            edges.append(edge)
            
            logging.info(f"📊 [GRAPH_EXPORT] Extracted {len(nodes)} nodes and {len(edges)} edges")
            return nodes, edges
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Error extracting graph: {e}")
            return nodes, edges
    
    async def build_networkx_graph(self, 
                                 context_filter: Optional[SemanticContext] = None,
                                 use_cache: bool = True) -> Optional[nx.Graph]:
        """
        Build a NetworkX graph from Cognee data
        
        Args:
            context_filter: Optional context filter
            use_cache: Whether to use cached graph if available
            
        Returns:
            NetworkX graph or None if not available
        """
        if not NETWORKX_AVAILABLE:
            logging.warning("⚠️ [GRAPH_EXPORT] NetworkX not available")
            return None
        
        # Check cache
        if use_cache and self.graph_cache and self.cache_timestamp:
            if datetime.now() - self.cache_timestamp < self.cache_duration:
                logging.info("📊 [GRAPH_EXPORT] Using cached graph")
                return self.graph_cache
        
        try:
            # Extract graph data
            nodes, edges = await self.extract_knowledge_graph(context_filter)
            
            # Build NetworkX graph
            G = nx.Graph()
            
            # Add nodes
            for node in nodes:
                G.add_node(node.id, 
                          label=node.label,
                          context=node.context,
                          node_type=node.node_type,
                          metadata=node.metadata or {})
            
            # Add edges
            for edge in edges:
                G.add_edge(edge.source, edge.target,
                          relationship=edge.relationship,
                          weight=edge.weight,
                          metadata=edge.metadata or {})
            
            # Update cache
            self.graph_cache = G
            self.cache_timestamp = datetime.now()
            
            logging.info(f"📊 [GRAPH_EXPORT] Built NetworkX graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Error building NetworkX graph: {e}")
            return None
    
    async def export_graph(self, 
                         format: ExportFormat,
                         context_filter: Optional[SemanticContext] = None,
                         output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Export the knowledge graph in the specified format
        
        Args:
            format: Export format
            context_filter: Optional context filter
            output_file: Optional output file path
            
        Returns:
            Export result with data or file path
        """
        try:
            if format == ExportFormat.NETWORKX:
                # Return NetworkX object
                graph = await self.build_networkx_graph(context_filter)
                return {
                    "success": bool(graph),
                    "format": format.value,
                    "data": graph
                }
            
            # Extract graph data
            nodes, edges = await self.extract_knowledge_graph(context_filter)
            
            if format == ExportFormat.D3JS:
                # D3.js compatible format
                d3_data = {
                    "nodes": [
                        {
                            "id": node.id,
                            "label": node.label,
                            "group": node.context,
                            "type": node.node_type
                        }
                        for node in nodes
                    ],
                    "links": [
                        {
                            "source": edge.source,
                            "target": edge.target,
                            "type": edge.relationship,
                            "value": edge.weight
                        }
                        for edge in edges
                    ]
                }
                
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump(d3_data, f, indent=2)
                
                return {
                    "success": True,
                    "format": format.value,
                    "data": d3_data,
                    "nodes": len(nodes),
                    "edges": len(edges)
                }
            
            elif format == ExportFormat.CYTOSCAPE:
                # Cytoscape.js format
                cyto_elements = []
                
                # Add nodes
                for node in nodes:
                    cyto_elements.append({
                        "data": {
                            "id": node.id,
                            "label": node.label,
                            "context": node.context,
                            "type": node.node_type
                        }
                    })
                
                # Add edges
                for edge in edges:
                    cyto_elements.append({
                        "data": {
                            "id": f"{edge.source}_{edge.target}",
                            "source": edge.source,
                            "target": edge.target,
                            "relationship": edge.relationship,
                            "weight": edge.weight
                        }
                    })
                
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump({"elements": cyto_elements}, f, indent=2)
                
                return {
                    "success": True,
                    "format": format.value,
                    "data": {"elements": cyto_elements},
                    "nodes": len(nodes),
                    "edges": len(edges)
                }
            
            elif format == ExportFormat.JSON_LD:
                # JSON-LD format with semantic web standards
                json_ld = {
                    "@context": {
                        "@vocab": "http://schema.org/",
                        "scb": "http://example.org/scb-cognee#"
                    },
                    "@graph": []
                }
                
                # Add nodes
                for node in nodes:
                    json_ld["@graph"].append({
                        "@id": node.id,
                        "@type": node.node_type,
                        "name": node.label,
                        "scb:context": node.context,
                        "scb:metadata": node.metadata or {}
                    })
                
                # Add relationships
                for edge in edges:
                    json_ld["@graph"].append({
                        "@type": "Relationship",
                        "scb:relationship": edge.relationship,
                        "source": {"@id": edge.source},
                        "target": {"@id": edge.target},
                        "weight": edge.weight
                    })
                
                if output_file:
                    with open(output_file, 'w') as f:
                        json.dump(json_ld, f, indent=2)
                
                return {
                    "success": True,
                    "format": format.value,
                    "data": json_ld,
                    "nodes": len(nodes),
                    "edges": len(edges)
                }
            
            elif format == ExportFormat.GRAPHML and NETWORKX_AVAILABLE:
                # GraphML format using NetworkX
                G = await self.build_networkx_graph(context_filter)
                if G and output_file:
                    nx.write_graphml(G, output_file)
                    return {
                        "success": True,
                        "format": format.value,
                        "file": output_file,
                        "nodes": G.number_of_nodes(),
                        "edges": G.number_of_edges()
                    }
            
            elif format == ExportFormat.GEXF and NETWORKX_AVAILABLE:
                # GEXF format for Gephi
                G = await self.build_networkx_graph(context_filter)
                if G and output_file:
                    nx.write_gexf(G, output_file)
                    return {
                        "success": True,
                        "format": format.value,
                        "file": output_file,
                        "nodes": G.number_of_nodes(),
                        "edges": G.number_of_edges()
                    }
            
            elif format == ExportFormat.DOT and NETWORKX_AVAILABLE:
                # Graphviz DOT format
                G = await self.build_networkx_graph(context_filter)
                if G and output_file:
                    nx.drawing.nx_agraph.write_dot(G, output_file)
                    return {
                        "success": True,
                        "format": format.value,
                        "file": output_file,
                        "nodes": G.number_of_nodes(),
                        "edges": G.number_of_edges()
                    }
            
            return {
                "success": False,
                "error": f"Format {format.value} not supported or dependencies missing"
            }
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Export error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_interactive_visualization(self,
                                               context_filter: Optional[SemanticContext] = None,
                                               output_file: str = "semantic_graph.html",
                                               physics: bool = True) -> Dict[str, Any]:
        """
        Generate an interactive HTML visualization using PyVis
        
        Args:
            context_filter: Optional context filter
            output_file: Output HTML file path
            physics: Enable physics simulation
            
        Returns:
            Result with file path
        """
        if not PYVIS_AVAILABLE:
            return {
                "success": False,
                "error": "PyVis not available - install with: pip install pyvis"
            }
        
        try:
            # Extract graph data
            nodes, edges = await self.extract_knowledge_graph(context_filter)
            
            # Create PyVis network
            net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
            
            # Configure physics
            if physics:
                net.barnes_hut(gravity=-80000, central_gravity=0.3, spring_length=250, spring_strength=0.001)
            
            # Add nodes with context-based colors
            context_colors = {
                "general_context": "#1f77b4",
                "s2_to_s1_messages": "#ff7f0e",
                "s1_to_s2_feedback": "#2ca02c",
                "tool_executions": "#d62728",
                "stimuli_context": "#9467bd",
                "agent_state": "#8c564b",
                "trading_finance": "#e377c2",
                "system_events": "#7f7f7f"
            }
            
            for node in nodes:
                color = context_colors.get(node.context, "#17a2b8")
                net.add_node(node.id, 
                           label=node.label,
                           color=color,
                           title=f"{node.context}\n{node.label}",
                           size=20 if node.node_type == "entity" else 15)
            
            # Add edges with relationship labels
            for edge in edges:
                net.add_edge(edge.source, edge.target,
                           title=edge.relationship,
                           width=edge.weight * 2)
            
            # Add options
            net.set_options("""
            var options = {
              "nodes": {
                "font": {
                  "size": 12,
                  "face": "Arial"
                }
              },
              "edges": {
                "color": {
                  "color": "#848484",
                  "highlight": "#848484",
                  "hover": "#848484"
                },
                "smooth": {
                  "type": "continuous"
                }
              },
              "physics": {
                "enabled": true,
                "solver": "barnes_hut"
              }
            }
            """)
            
            # Save the visualization
            net.show(output_file)
            
            return {
                "success": True,
                "file": output_file,
                "nodes": len(nodes),
                "edges": len(edges),
                "contexts": list(set(node.context for node in nodes))
            }
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Visualization error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_graph_metrics(self, context_filter: Optional[SemanticContext] = None) -> Dict[str, Any]:
        """
        Analyze graph metrics and statistics
        
        Args:
            context_filter: Optional context filter
            
        Returns:
            Graph metrics and analysis
        """
        if not NETWORKX_AVAILABLE:
            return {
                "success": False,
                "error": "NetworkX not available for graph analysis"
            }
        
        try:
            G = await self.build_networkx_graph(context_filter)
            if not G:
                return {"success": False, "error": "Failed to build graph"}
            
            # Basic metrics
            metrics = {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "density": nx.density(G),
                "is_connected": nx.is_connected(G),
                "number_of_components": nx.number_connected_components(G)
            }
            
            # Centrality measures
            if G.number_of_nodes() > 0:
                degree_centrality = nx.degree_centrality(G)
                top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
                
                metrics["top_nodes_by_degree"] = [
                    {
                        "node": G.nodes[node_id].get("label", node_id),
                        "centrality": score
                    }
                    for node_id, score in top_nodes
                ]
                
                # Betweenness centrality (for smaller graphs)
                if G.number_of_nodes() < 100:
                    betweenness = nx.betweenness_centrality(G)
                    top_betweenness = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]
                    metrics["top_nodes_by_betweenness"] = [
                        {
                            "node": G.nodes[node_id].get("label", node_id),
                            "centrality": score
                        }
                        for node_id, score in top_betweenness
                    ]
            
            # Context distribution
            context_counts = {}
            for node_id, data in G.nodes(data=True):
                context = data.get("context", "unknown")
                context_counts[context] = context_counts.get(context, 0) + 1
            
            metrics["context_distribution"] = context_counts
            
            # Relationship types
            relationship_counts = {}
            for u, v, data in G.edges(data=True):
                rel = data.get("relationship", "unknown")
                relationship_counts[rel] = relationship_counts.get(rel, 0) + 1
            
            metrics["relationship_distribution"] = relationship_counts
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except Exception as e:
            logging.error(f"❌ [GRAPH_EXPORT] Analysis error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            "service": "graph_export",
            "networkx_available": NETWORKX_AVAILABLE,
            "pyvis_available": PYVIS_AVAILABLE,
            "cognee_connected": bool(self.cognee_direct or self.cognee_service),
            "cache_valid": bool(self.cache_timestamp and datetime.now() - self.cache_timestamp < self.cache_duration),
            "supported_formats": [f.value for f in ExportFormat]
        }


# Global service instance
_graph_export_service: Optional[GraphExportService] = None


async def get_graph_export_service() -> Optional[GraphExportService]:
    """Get or create the global graph export service"""
    global _graph_export_service
    
    if _graph_export_service is None:
        _graph_export_service = GraphExportService()
        initialized = await _graph_export_service.initialize()
        if not initialized:
            _graph_export_service = None
    
    return _graph_export_service