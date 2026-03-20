"""Graph search functionality for GraphRAG."""

import re
from typing import List, Dict, Any, Tuple, Set


def extract_entities_simple(text: str) -> Set[str]:
    """
    Simple entity extraction using heuristics.
    Looks for company names, stock tickers, and financial terms.
    """
    entities = set()
    
    # Stock ticker patterns (3-5 uppercase letters)
    ticker_pattern = r'\b[A-Z]{3,5}\b'
    tickers = re.findall(ticker_pattern, text)
    entities.update(tickers)
    
    # Company names (capitalized words, often followed by Inc, Corp, LLC, etc.)
    company_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|Corporation|LLC|Company|Ltd)\.?)?'
    companies = re.findall(company_pattern, text)
    entities.update(companies)
    
    # Remove common false positives
    stop_words = {
        'The', 'This', 'That', 'These', 'Those', 'We', 'Our', 'Inc', 'Corp', 
        'Corporation', 'LLC', 'Company', 'Ltd', 'And', 'Or', 'But', 'For',
        'As', 'Of', 'In', 'On', 'At', 'By', 'From', 'To', 'With', 'During'
    }
    entities = {e for e in entities if e not in stop_words and len(e) > 2}
    
    return entities


class GraphSearcher:
    """Search functionality for knowledge graphs."""
    
    def __init__(self, graph_data: Dict[str, Any], communities_data: List[Dict[str, Any]]):
        self.graph = graph_data
        self.communities = communities_data
        
        # Build entity to community mapping for faster lookup
        self.entity_to_community = {}
        for community in self.communities:
            community_id = community.get('id')
            for entity in community.get('entities', []):
                self.entity_to_community[entity] = community_id
    
    def local_search(self, query: str, max_results: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Local search: Find entities in query and retrieve connected nodes.
        """
        # Extract entities from query
        query_entities = extract_entities_simple(query)
        
        # Find matching nodes in graph
        matching_nodes = []
        connected_edges = []
        
        nodes = self.graph.get('nodes', [])
        edges = self.graph.get('edges', [])
        
        # Find nodes that match query entities
        for node in nodes:
            node_name = node.get('name', '').lower()
            for entity in query_entities:
                if entity.lower() in node_name or node_name in entity.lower():
                    matching_nodes.append(node)
                    break
        
        # Find edges connected to matching nodes
        matching_node_ids = {node.get('id') for node in matching_nodes}
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source in matching_node_ids or target in matching_node_ids:
                connected_edges.append(edge)
        
        # Build local context
        local_context = []
        for node in matching_nodes[:max_results]:
            context_item = {
                'type': 'entity',
                'name': node.get('name', ''),
                'description': node.get('description', ''),
                'properties': node.get('properties', {})
            }
            local_context.append(context_item)
        
        # Add relationship information
        for edge in connected_edges[:max_results * 2]:
            relation_item = {
                'type': 'relation',
                'source': edge.get('source', ''),
                'target': edge.get('target', ''),
                'relationship': edge.get('relationship', ''),
                'description': edge.get('description', '')
            }
            local_context.append(relation_item)
        
        trace = {
            'search_type': 'local',
            'query_entities': list(query_entities),
            'matching_nodes_count': len(matching_nodes),
            'connected_edges_count': len(connected_edges),
            'context_items': len(local_context)
        }
        
        return local_context, trace
    
    def global_search(self, query: str, max_results: int = 3) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Global search: Find relevant community summaries.
        """
        query_lower = query.lower()
        community_scores = []
        
        # Score communities based on summary relevance
        for community in self.communities:
            summary = community.get('summary', '').lower()
            title = community.get('title', '').lower()
            
            # Simple scoring based on keyword overlap
            score = 0
            query_words = set(query_lower.split())
            summary_words = set(summary.split())
            title_words = set(title.split())
            
            # Title matches are more important
            title_overlap = len(query_words.intersection(title_words))
            summary_overlap = len(query_words.intersection(summary_words))
            
            score = title_overlap * 2 + summary_overlap
            
            if score > 0:
                community_scores.append((community, score))
        
        # Sort by relevance and take top results
        community_scores.sort(key=lambda x: x[1], reverse=True)
        top_communities = community_scores[:max_results]
        
        # Build global context
        global_context = []
        for community, score in top_communities:
            context_item = {
                'type': 'community',
                'id': community.get('id'),
                'title': community.get('title', ''),
                'summary': community.get('summary', ''),
                'entities_count': len(community.get('entities', [])),
                'relevance_score': score
            }
            global_context.append(context_item)
        
        trace = {
            'search_type': 'global',
            'communities_scored': len(community_scores),
            'top_communities_count': len(top_communities),
            'community_scores': [score for _, score in top_communities]
        }
        
        return global_context, trace
    
    def combined_search(
        self, 
        query: str, 
        search_mode: str = "both"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Combined local and global search based on mode.
        """
        if search_mode == "local":
            return self.local_search(query)
        elif search_mode == "global":
            return self.global_search(query)
        else:  # "both"
            local_results, local_trace = self.local_search(query, max_results=3)
            global_results, global_trace = self.global_search(query, max_results=2)
            
            combined_results = local_results + global_results
            combined_trace = {
                'search_mode': 'both',
                'local': local_trace,
                'global': global_trace,
                'total_results': len(combined_results)
            }
            
            return combined_results, combined_trace