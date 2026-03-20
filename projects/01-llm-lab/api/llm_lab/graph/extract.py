"""Simple graph extraction from text using heuristics."""

import re
import json
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any
from pathlib import Path


class SimpleGraphExtractor:
    """Extract knowledge graph using simple heuristics (no LLM required)."""
    
    def __init__(self):
        # Common financial/business entities patterns
        self.entity_patterns = [
            (r'\b[A-Z]{2,5}\b', 'ticker'),  # Stock tickers
            (r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|Corporation|LLC|Company|Ltd))\.?', 'company'),
            (r'\$\d+(?:\.\d+)?\s*(?:billion|million|thousand)?', 'financial_amount'),
            (r'\d{4}(?:\s+fiscal\s+year)?', 'year'),
            (r'(?:revenue|profit|earnings|sales|income|margin)', 'financial_metric'),
        ]
        
    def extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text using pattern matching."""
        entities = []
        entity_id = 0
        
        for pattern, entity_type in self.entity_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity_text = match.group(0).strip()
                
                # Skip very short matches or common words
                if len(entity_text) < 2 or entity_text.lower() in {'the', 'and', 'for', 'inc', 'corp'}:
                    continue
                
                entities.append({
                    'id': f'entity_{entity_id}',
                    'name': entity_text,
                    'type': entity_type,
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'context': text[max(0, match.start()-50):match.end()+50]
                })
                entity_id += 1
        
        return entities
    
    def build_cooccurrence_graph(
        self, 
        all_entities: List[Dict[str, Any]], 
        chunks: List[Dict[str, Any]],
        window_size: int = 100
    ) -> Dict[str, Any]:
        """Build co-occurrence graph based on entity proximity."""
        # Create entity lookup by position
        entity_lookup = defaultdict(list)
        
        for entity in all_entities:
            chunk_id = entity.get('chunk_id')
            if chunk_id:
                entity_lookup[chunk_id].append(entity)
        
        # Build co-occurrence relationships
        cooccurrences = Counter()
        relationships = []
        relationship_id = 0
        
        for chunk_id, chunk_entities in entity_lookup.items():
            # Find co-occurring entities within same chunk
            for i, entity1 in enumerate(chunk_entities):
                for entity2 in chunk_entities[i+1:]:
                    # Check if entities are within window
                    pos_diff = abs(entity1['start_pos'] - entity2['start_pos'])
                    if pos_diff <= window_size:
                        # Create bidirectional relationship
                        pair = tuple(sorted([entity1['name'], entity2['name']]))
                        cooccurrences[pair] += 1
                        
                        relationships.append({
                            'id': f'rel_{relationship_id}',
                            'source': entity1['id'],
                            'target': entity2['id'],
                            'relationship': 'co_occurs_with',
                            'weight': 1,
                            'chunk_id': chunk_id,
                            'description': f"Co-occurs in same document context"
                        })
                        relationship_id += 1
        
        # Consolidate entities (remove duplicates by name)
        unique_entities = {}
        for entity in all_entities:
            name = entity['name'].lower()
            if name not in unique_entities:
                unique_entities[name] = {
                    'id': entity['id'],
                    'name': entity['name'],
                    'type': entity['type'],
                    'frequency': 1,
                    'properties': {}
                }
            else:
                unique_entities[name]['frequency'] += 1
        
        # Create final graph structure
        nodes = list(unique_entities.values())
        
        # Filter relationships to only include frequent co-occurrences
        min_cooccurrence = 2
        filtered_relationships = []
        
        for rel in relationships:
            source_entity = next((e for e in all_entities if e['id'] == rel['source']), None)
            target_entity = next((e for e in all_entities if e['id'] == rel['target']), None)
            
            if source_entity and target_entity:
                pair = tuple(sorted([source_entity['name'], target_entity['name']]))
                if cooccurrences[pair] >= min_cooccurrence:
                    rel['weight'] = cooccurrences[pair]
                    filtered_relationships.append(rel)
        
        graph = {
            'nodes': nodes,
            'edges': filtered_relationships,
            'metadata': {
                'extraction_method': 'heuristic_cooccurrence',
                'total_entities': len(nodes),
                'total_relationships': len(filtered_relationships),
                'window_size': window_size,
                'min_cooccurrence_threshold': min_cooccurrence
            }
        }
        
        return graph
    
    def create_communities(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create simple communities based on entity types and relationships."""
        nodes = graph['nodes']
        edges = graph['edges']
        
        # Group entities by type
        type_groups = defaultdict(list)
        for node in nodes:
            type_groups[node['type']].append(node)
        
        # Create communities based on entity types
        communities = []
        community_id = 0
        
        for entity_type, entities in type_groups.items():
            if len(entities) >= 2:  # Only create communities with multiple entities
                # Find highly connected entities within type
                entity_names = [e['name'] for e in entities]
                
                # Get relationships within this type
                type_edges = [
                    e for e in edges 
                    if any(node['id'] == e['source'] and node['name'] in entity_names for node in nodes) and
                       any(node['id'] == e['target'] and node['name'] in entity_names for node in nodes)
                ]
                
                if type_edges or len(entities) <= 5:  # Small groups or connected groups
                    community_title = f"{entity_type.replace('_', ' ').title()} Entities"
                    
                    community = {
                        'id': f'community_{community_id}',
                        'title': community_title,
                        'summary': f"Collection of {len(entities)} {entity_type} entities found in the documents, including relationships and co-occurrences.",
                        'entities': entity_names,
                        'entity_count': len(entities),
                        'relationship_count': len(type_edges),
                        'type_focus': entity_type
                    }
                    communities.append(community)
                    community_id += 1
        
        # Create a "cross-type" community for highly connected entities across types
        high_degree_nodes = []
        for node in nodes:
            node_degree = len([e for e in edges if e['source'] == node['id'] or e['target'] == node['id']])
            if node_degree >= 3:  # Entities with 3+ connections
                high_degree_nodes.append(node['name'])
        
        if len(high_degree_nodes) >= 3:
            communities.append({
                'id': f'community_{community_id}',
                'title': 'Key Connected Entities',
                'summary': f"Highly connected entities appearing frequently across documents: {', '.join(high_degree_nodes[:5])}{'...' if len(high_degree_nodes) > 5 else ''}",
                'entities': high_degree_nodes,
                'entity_count': len(high_degree_nodes),
                'relationship_count': len([e for e in edges if any(node['name'] in high_degree_nodes for node in nodes if node['id'] in [e['source'], e['target']])]),
                'type_focus': 'cross_type'
            })
        
        return communities
    
    def extract_from_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Extract graph and communities from document chunks.
        
        Returns:
            Tuple of (graph_data, communities_data)
        """
        print("Extracting entities from chunks...")
        
        all_entities = []
        
        for chunk in chunks:
            chunk_entities = self.extract_entities_from_text(chunk['text'])
            
            # Add chunk reference to entities
            for entity in chunk_entities:
                entity['chunk_id'] = chunk['id']
                entity['source'] = chunk.get('source', 'unknown')
            
            all_entities.extend(chunk_entities)
        
        print(f"Extracted {len(all_entities)} raw entities")
        
        # Build co-occurrence graph
        print("Building co-occurrence graph...")
        graph = self.build_cooccurrence_graph(all_entities, chunks)
        
        # Create communities  
        print("Creating entity communities...")
        communities = self.create_communities(graph)
        
        print(f"Created graph with {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
        print(f"Created {len(communities)} communities")
        
        return graph, communities