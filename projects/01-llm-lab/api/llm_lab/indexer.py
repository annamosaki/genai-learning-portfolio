"""Main indexing pipeline for LLM Lab."""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any
from .config import settings
from .fetch_filings import FilingsFetcher
from .retrieval.chunking import chunk_document
from .retrieval.embed import EmbeddingManager
from .retrieval.bm25 import BM25
from .graph.extract import SimpleGraphExtractor


class LLMLabIndexer:
    """Main indexer for building all search indexes and data structures."""
    
    def __init__(self):
        self.corpus_dir = Path(settings.corpus_dir)
        self.index_dir = Path(settings.index_dir)
        self.embedding_manager = EmbeddingManager()
        self.graph_extractor = SimpleGraphExtractor()
        
    async def build_all(self, fetch_corpus: bool = True):
        """
        Build all indexes and data structures.
        
        Args:
            fetch_corpus: Whether to fetch/create corpus files first
        """
        print("🚀 Starting LLM Lab indexing pipeline...")
        start_time = time.time()
        
        # Step 1: Ensure corpus exists
        if fetch_corpus:
            await self._ensure_corpus()
        
        # Step 2: Load and chunk documents
        chunks = await self._create_chunks()
        if not chunks:
            print("❌ No chunks created - stopping indexing")
            return
        
        # Step 3: Create embeddings
        await self._create_embeddings(chunks)
        
        # Step 4: Build BM25 index
        await self._build_bm25_index(chunks)
        
        # Step 5: Extract financial figures
        await self._extract_figures(chunks)
        
        # Step 6: Build graph and communities
        await self._build_graph(chunks)
        
        elapsed = time.time() - start_time
        print(f"✅ Indexing complete! Total time: {elapsed:.1f}s")
        
        # Show summary
        self._print_index_summary()
    
    async def _ensure_corpus(self):
        """Ensure corpus files exist."""
        print("\n📄 Checking corpus files...")
        
        if not self.corpus_dir.exists():
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
        
        existing_files = list(self.corpus_dir.glob("*.md"))
        
        if len(existing_files) < 3:
            print("Creating missing corpus files...")
            fetcher = FilingsFetcher()
            await fetcher.fetch_all_filings()
        else:
            print(f"Found {len(existing_files)} corpus files")
    
    async def _create_chunks(self) -> List[Dict[str, Any]]:
        """Load documents and create chunks."""
        print("\n✂️  Creating document chunks...")
        
        corpus_files = list(self.corpus_dir.glob("*.md"))
        if not corpus_files:
            print("❌ No corpus files found")
            return []
        
        all_chunks = []
        
        for file_path in corpus_files:
            print(f"Processing {file_path.name}...")
            
            try:
                with open(file_path, 'r') as f:
                    text = f.read()
                
                # Create both naive and smart chunks
                naive_chunks = chunk_document(
                    text, 
                    source=file_path.name,
                    method="naive",
                    chunk_size=800,
                    overlap=100
                )
                
                smart_chunks = chunk_document(
                    text,
                    source=file_path.name, 
                    method="smart",
                    chunk_size=800,
                    overlap=100
                )
                
                # Use smart chunks as primary, naive as fallback
                file_chunks = smart_chunks if smart_chunks else naive_chunks
                
                print(f"  Created {len(file_chunks)} chunks")
                all_chunks.extend(file_chunks)
                
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
        
        print(f"Total chunks created: {len(all_chunks)}")
        
        # Save chunks to JSON
        self.index_dir.mkdir(parents=True, exist_ok=True)
        chunks_file = self.index_dir / "chunks.json"
        
        with open(chunks_file, 'w') as f:
            json.dump(all_chunks, f, indent=2)
        
        print(f"Chunks saved to {chunks_file}")
        return all_chunks
    
    async def _create_embeddings(self, chunks: List[Dict[str, Any]]):
        """Create embeddings for chunks."""
        print("\n🔢 Creating embeddings...")
        
        if not chunks:
            print("No chunks to embed")
            return
        
        try:
            embeddings = await self.embedding_manager.create_embeddings(chunks)
            
            embeddings_file = self.index_dir / "embeddings.npy"
            self.embedding_manager.save_embeddings(embeddings, embeddings_file)
            
        except Exception as e:
            print(f"Error creating embeddings: {e}")
    
    async def _build_bm25_index(self, chunks: List[Dict[str, Any]]):
        """Build BM25 search index."""
        print("\n🔍 Building BM25 index...")
        
        if not chunks:
            print("No chunks for BM25 indexing")
            return
        
        try:
            # Extract texts for BM25
            texts = [chunk['text'] for chunk in chunks]
            
            # Build BM25 index
            bm25 = BM25()
            bm25.fit(texts)
            
            # Save BM25 index
            bm25_file = self.index_dir / "bm25.json"
            with open(bm25_file, 'w') as f:
                json.dump(bm25.to_dict(), f, indent=2)
            
            print(f"BM25 index saved to {bm25_file}")
            
        except Exception as e:
            print(f"Error building BM25 index: {e}")
    
    async def _extract_figures(self, chunks: List[Dict[str, Any]]):
        """Extract financial figures from chunks."""
        print("\n💰 Extracting financial figures...")
        
        figures = {}
        
        # Simple regex patterns for financial figures
        patterns = [
            (r'revenue[:\s]+\$?([\d,\.]+)\s*(billion|million|thousand)?', 'revenue'),
            (r'net\s+income[:\s]+\$?([\d,\.]+)\s*(billion|million|thousand)?', 'net_income'),
            (r'operating\s+income[:\s]+\$?([\d,\.]+)\s*(billion|million|thousand)?', 'operating_income'),
            (r'gross\s+margin[:\s]+([\d,\.]+)%?', 'gross_margin'),
            (r'operating\s+margin[:\s]+([\d,\.]+)%?', 'operating_margin'),
            (r'eps[:\s]+\$?([\d,\.]+)', 'eps'),
            (r'diluted\s+eps[:\s]+\$?([\d,\.]+)', 'diluted_eps'),
        ]
        
        for chunk in chunks:
            text = chunk['text'].lower()
            source = chunk.get('source', 'unknown')
            
            # Extract company from source filename
            company_match = re.search(r'(NVDA|AAPL|MSFT)', source.upper())
            company = company_match.group(1) if company_match else 'UNKNOWN'
            
            if company not in figures:
                figures[company] = {}
            
            for pattern, metric_name in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        value_str = match.group(1).replace(',', '')
                        value = float(value_str)
                        
                        # Apply scale multiplier
                        if len(match.groups()) > 1 and match.group(2):
                            scale = match.group(2).lower()
                            if scale == 'billion':
                                value *= 1e9
                            elif scale == 'million':
                                value *= 1e6
                            elif scale == 'thousand':
                                value *= 1e3
                        
                        # Store the highest value found (assuming latest/most relevant)
                        if metric_name not in figures[company] or value > figures[company][metric_name]:
                            figures[company][metric_name] = value
                            
                    except (ValueError, IndexError):
                        continue
        
        # Save figures
        figures_file = self.index_dir / "figures.json"
        with open(figures_file, 'w') as f:
            json.dump(figures, f, indent=2)
        
        total_figures = sum(len(company_data) for company_data in figures.values())
        print(f"Extracted {total_figures} financial figures across {len(figures)} companies")
        print(f"Figures saved to {figures_file}")
    
    async def _build_graph(self, chunks: List[Dict[str, Any]]):
        """Build knowledge graph and communities."""
        print("\n🕸️  Building knowledge graph...")
        
        if not chunks:
            print("No chunks for graph building")
            return
        
        try:
            # Extract graph and communities
            graph_data, communities_data = self.graph_extractor.extract_from_chunks(chunks)
            
            # Save graph
            graph_file = self.index_dir / "graph.json"
            with open(graph_file, 'w') as f:
                json.dump(graph_data, f, indent=2)
            
            # Save communities
            communities_file = self.index_dir / "communities.json"
            with open(communities_file, 'w') as f:
                json.dump(communities_data, f, indent=2)
            
            print(f"Graph saved to {graph_file}")
            print(f"Communities saved to {communities_file}")
            
        except Exception as e:
            print(f"Error building graph: {e}")
    
    def _print_index_summary(self):
        """Print summary of created indexes."""
        print("\n📊 Index Summary:")
        print("=" * 50)
        
        # Check each index file
        index_files = [
            ("chunks.json", "Document chunks"),
            ("embeddings.npy", "Vector embeddings"),
            ("bm25.json", "BM25 search index"),
            ("figures.json", "Financial figures"),
            ("graph.json", "Knowledge graph"),
            ("communities.json", "Entity communities")
        ]
        
        for filename, description in index_files:
            filepath = self.index_dir / filename
            if filepath.exists():
                if filename.endswith('.json'):
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                count = len(data)
                            elif isinstance(data, dict):
                                count = len(data)
                            else:
                                count = "✓"
                        print(f"✅ {description}: {count} items")
                    except:
                        print(f"✅ {description}: ✓")
                else:
                    print(f"✅ {description}: ✓")
            else:
                print(f"❌ {description}: Missing")
        
        print("\n🎉 Ready to start the LLM Lab API!")
        print("Run: python -m llm_lab.app")


async def main():
    """CLI entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("LLM Lab Indexer")
        print("Usage: python -m llm_lab.indexer [command]")
        print("")
        print("Commands:")
        print("  build --all    Build all indexes (default)")
        print("  build --no-fetch    Build indexes without fetching corpus")
        print("  --help         Show this help")
        return
    
    indexer = LLMLabIndexer()
    
    # Parse arguments
    fetch_corpus = True
    if len(sys.argv) > 2 and sys.argv[2] == "--no-fetch":
        fetch_corpus = False
    
    await indexer.build_all(fetch_corpus=fetch_corpus)


if __name__ == "__main__":
    asyncio.run(main())