"""Document chunking strategies for RAG systems."""

import re
from typing import List, Dict, Any, Tuple


def naive_chunking(text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Naive fixed-size chunking with character-based splitting.
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap between consecutive chunks
    
    Returns:
        List of chunk dictionaries with text, start_pos, end_pos
    """
    if not text or chunk_size <= 0:
        return []
    
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to break at word boundary if possible
        if end < len(text):
            # Look for last space within last 50 characters
            last_space = text.rfind(' ', end - 50, end)
            if last_space > start:
                end = last_space
        
        chunk_text = text[start:end].strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                'id': f'naive_chunk_{chunk_id}',
                'text': chunk_text,
                'start_pos': start,
                'end_pos': end,
                'method': 'naive',
                'size': len(chunk_text)
            })
            chunk_id += 1
        
        # Move start position with overlap
        start = max(start + 1, end - overlap)
        
        # Prevent infinite loop
        if start >= end:
            break
    
    return chunks


def smart_chunking(text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Smart heading-aware chunking that respects document structure.
    
    Tries to break at:
    1. Markdown headings (# ## ###)
    2. Double newlines (paragraph breaks)
    3. Single newlines
    4. Sentence endings
    5. Word boundaries
    """
    if not text or chunk_size <= 0:
        return []
    
    chunks = []
    chunk_id = 0
    
    # Split text into sections by headings first
    sections = _split_by_headings(text)
    
    for section in sections:
        section_chunks = _chunk_section(section, chunk_size, overlap, chunk_id)
        chunks.extend(section_chunks)
        chunk_id += len(section_chunks)
    
    return chunks


def _split_by_headings(text: str) -> List[Dict[str, Any]]:
    """Split text into sections based on markdown headings."""
    # Pattern to match markdown headings
    heading_pattern = r'^(#{1,6})\s+(.+)$'
    
    sections = []
    current_section = {'heading': '', 'level': 0, 'content': '', 'start_pos': 0}
    
    lines = text.split('\n')
    pos = 0
    
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        
        heading_match = re.match(heading_pattern, line, re.MULTILINE)
        
        if heading_match:
            # Save previous section if it has content
            if current_section['content'].strip():
                current_section['end_pos'] = pos
                sections.append(current_section)
            
            # Start new section
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2)
            
            current_section = {
                'heading': heading_text,
                'level': level,
                'content': line + '\n',
                'start_pos': pos
            }
        else:
            current_section['content'] += line + '\n'
        
        pos += line_len
    
    # Add final section
    if current_section['content'].strip():
        current_section['end_pos'] = pos
        sections.append(current_section)
    
    return sections


def _chunk_section(
    section: Dict[str, Any], 
    chunk_size: int, 
    overlap: int, 
    start_chunk_id: int
) -> List[Dict[str, Any]]:
    """Chunk a single section with smart boundary detection."""
    content = section['content']
    heading = section.get('heading', '')
    
    if len(content) <= chunk_size:
        # Section fits in one chunk
        return [{
            'id': f'smart_chunk_{start_chunk_id}',
            'text': content.strip(),
            'start_pos': section['start_pos'],
            'end_pos': section.get('end_pos', section['start_pos'] + len(content)),
            'method': 'smart',
            'heading': heading,
            'section_level': section.get('level', 0),
            'size': len(content.strip())
        }]
    
    # Need to split section into multiple chunks
    chunks = []
    chunk_id = start_chunk_id
    start = 0
    
    while start < len(content):
        end = min(start + chunk_size, len(content))
        
        # Try to find good break point
        break_point = _find_break_point(content, start, end)
        if break_point > start:
            end = break_point
        
        chunk_text = content[start:end].strip()
        
        # Include heading in first chunk of section
        if chunk_id == start_chunk_id and heading:
            if not chunk_text.startswith(heading):
                chunk_text = f"# {heading}\n\n{chunk_text}"
        
        if chunk_text:
            chunks.append({
                'id': f'smart_chunk_{chunk_id}',
                'text': chunk_text,
                'start_pos': section['start_pos'] + start,
                'end_pos': section['start_pos'] + end,
                'method': 'smart',
                'heading': heading,
                'section_level': section.get('level', 0),
                'size': len(chunk_text)
            })
            chunk_id += 1
        
        start = max(start + 1, end - overlap)
        if start >= end:
            break
    
    return chunks


def _find_break_point(text: str, start: int, end: int) -> int:
    """Find the best break point within a range using multiple strategies."""
    if end >= len(text):
        return end
    
    search_range = max(50, int((end - start) * 0.1))  # Search in last 10% or 50 chars
    search_start = max(start, end - search_range)
    
    # Strategy 1: Double newline (paragraph break)
    double_newline = text.rfind('\n\n', search_start, end)
    if double_newline > start:
        return double_newline + 2
    
    # Strategy 2: Single newline
    single_newline = text.rfind('\n', search_start, end)
    if single_newline > start:
        return single_newline + 1
    
    # Strategy 3: Sentence ending
    sentence_endings = ['. ', '! ', '? ']
    for ending in sentence_endings:
        pos = text.rfind(ending, search_start, end)
        if pos > start:
            return pos + len(ending)
    
    # Strategy 4: Word boundary
    space_pos = text.rfind(' ', search_start, end)
    if space_pos > start:
        return space_pos + 1
    
    # Fallback: hard break at end
    return end


def chunk_document(
    text: str, 
    source: str = "unknown",
    method: str = "smart",
    chunk_size: int = 800,
    overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Main document chunking function.
    
    Args:
        text: Document text to chunk
        source: Source identifier for the document
        method: Chunking method ('naive' or 'smart')
        chunk_size: Target chunk size in characters
        overlap: Overlap between chunks
    
    Returns:
        List of enriched chunk dictionaries
    """
    if method == "naive":
        chunks = naive_chunking(text, chunk_size, overlap)
    else:
        chunks = smart_chunking(text, chunk_size, overlap)
    
    # Enrich chunks with metadata
    for chunk in chunks:
        chunk['source'] = source
        chunk['chunk_size_target'] = chunk_size
        chunk['overlap'] = overlap
    
    return chunks