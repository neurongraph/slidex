"""
Graph visualization utilities for LightRAG knowledge graph.
"""

import json
from typing import Dict, Any, List
from pathlib import Path

from slidex.config import settings
from slidex.logging_config import logger


class GraphVisualizer:
    """Visualize LightRAG knowledge graph."""
    
    @staticmethod
    def export_graph_data() -> Dict[str, Any]:
        """
        Export graph data in a format suitable for visualization.
        
        Returns:
            Dict with nodes and edges in Cytoscape.js format
        """
        try:
            # Check if LightRAG graph files exist
            working_dir = settings.lightrag_working_dir
            graph_file = working_dir / "graph_chunk_entity_relation.graphml"
            
            if not graph_file.exists():
                logger.warning("LightRAG graph file not found. Run ingestion first.")
                return {"nodes": [], "edges": []}
            
            # Load and parse the graph
            import networkx as nx
            
            # LightRAG stores graph as GraphML
            G = nx.read_graphml(str(graph_file))
            
            # Convert to Cytoscape.js format
            nodes = []
            edges = []
            
            # Extract nodes
            for node_id, node_data in G.nodes(data=True):
                node_type = node_data.get('type', 'unknown')
                label = node_data.get('label', node_id)
                
                nodes.append({
                    "data": {
                        "id": str(node_id),
                        "label": label,
                        "type": node_type,
                        "description": node_data.get('description', ''),
                    }
                })
            
            # Extract edges
            for source, target, edge_data in G.edges(data=True):
                edge_type = edge_data.get('type', 'related_to')
                weight = edge_data.get('weight', 1.0)
                
                edges.append({
                    "data": {
                        "source": str(source),
                        "target": str(target),
                        "label": edge_type,
                        "weight": weight,
                    }
                })
            
            logger.info(f"Exported graph: {len(nodes)} nodes, {len(edges)} edges")
            
            return {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "node_types": _count_node_types(nodes),
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting graph data: {e}")
            return {"nodes": [], "edges": [], "error": str(e)}
    
    @staticmethod
    def get_graph_stats() -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        try:
            working_dir = settings.lightrag_working_dir
            graph_file = working_dir / "graph_chunk_entity_relation.graphml"
            
            if not graph_file.exists():
                return {"error": "Graph not found"}
            
            import networkx as nx
            G = nx.read_graphml(str(graph_file))
            
            stats = {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "density": nx.density(G),
                "is_directed": G.is_directed(),
            }
            
            # Add degree statistics if graph is not empty
            if G.number_of_nodes() > 0:
                degrees = [d for _, d in G.degree()]
                stats["avg_degree"] = sum(degrees) / len(degrees)
                stats["max_degree"] = max(degrees)
                stats["min_degree"] = min(degrees)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {"error": str(e)}


def _count_node_types(nodes: List[Dict]) -> Dict[str, int]:
    """Count nodes by type."""
    type_counts = {}
    for node in nodes:
        node_type = node["data"].get("type", "unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    return type_counts


# Global instance
graph_visualizer = GraphVisualizer()
