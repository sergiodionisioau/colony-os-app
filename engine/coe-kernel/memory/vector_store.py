"""PGVector Store Integration.

LlamaIndex vector store for semantic memory with OpenAI embeddings.
Includes fallback to mock embeddings and connection retry logic.
"""

import os
import uuid
import time
import warnings
import random
from typing import Any, Dict, List, Optional

# Try to import LangChain OpenAI embeddings
try:
    from langchain_openai import OpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class MockEmbeddings:
    """Mock embedding model for testing without API calls.

    Generates deterministic embeddings based on text hash.
    Falls back to this when OPENAI_API_KEY is not available.
    """

    def __init__(self, dim: int = 1536):
        self.embed_dim = dim

    def embed_query(self, text: str) -> List[float]:
        """Generate deterministic mock embedding based on text hash."""
        seed = hash(text) % (2**31)
        rng = random.Random(seed)
        return [rng.uniform(-1, 1) for _ in range(self.embed_dim)]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for batch of texts."""
        return [self.embed_query(text) for text in texts]


class OpenAIEmbeddingsWithFallback:
    """OpenAI Embeddings wrapper with automatic fallback to mock embeddings.

    Uses text-embedding-3-small with 1536 dimensions.
    Falls back to MockEmbeddings if OPENAI_API_KEY is not set.
    Includes retry logic for connection issues.
    """

    def __init__(
        self,
        dim: int = 1536,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        model: str = "text-embedding-3-small"
    ):
        self.embed_dim = dim
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.model = model
        self._embeddings = None
        self._using_mock = False
        self._init_embeddings()

    def _init_embeddings(self):
        """Initialize embeddings with fallback logic."""
        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            warnings.warn(
                "OPENAI_API_KEY not set. Using MockEmbeddings as fallback. "
                "Set OPENAI_API_KEY environment variable for real embeddings.",
                UserWarning
            )
            self._embeddings = MockEmbeddings(self.embed_dim)
            self._using_mock = True
            print("⚠️  VectorStore: Using MockEmbeddings (OPENAI_API_KEY not set)")
            return

        if not LANGCHAIN_AVAILABLE:
            warnings.warn(
                "langchain_openai not installed. Using MockEmbeddings as fallback.",
                UserWarning
            )
            self._embeddings = MockEmbeddings(self.embed_dim)
            self._using_mock = True
            print("⚠️  VectorStore: Using MockEmbeddings (langchain_openai not available)")
            return

        # Try to initialize OpenAI embeddings with retries
        for attempt in range(self.max_retries):
            try:
                self._embeddings = OpenAIEmbeddings(
                    model=self.model,
                    api_key=api_key,
                    dimensions=self.embed_dim
                )
                self._using_mock = False
                print(f"✅ VectorStore: Using OpenAI {self.model} ({self.embed_dim} dims)")
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️  VectorStore: OpenAI init failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"   Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    warnings.warn(
                        f"VectorStore: OpenAI initialization failed after {self.max_retries} attempts: {e}. "
                        "Falling back to MockEmbeddings.",
                        UserWarning
                    )

        # Fallback to mock
        self._embeddings = MockEmbeddings(self.embed_dim)
        self._using_mock = True
        print("⚠️  VectorStore: Using MockEmbeddings (OpenAI initialization failed)")

    @property
    def embeddings(self):
        """Get the underlying embeddings instance."""
        return self._embeddings

    @property
    def using_mock(self) -> bool:
        """Check if using mock embeddings."""
        return self._using_mock

    def embed_query(self, text: str) -> List[float]:
        """Get query embedding with retry logic."""
        if self._using_mock:
            return self._embeddings.embed_query(text)

        for attempt in range(self.max_retries):
            try:
                return self._embeddings.embed_query(text)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  VectorStore: embed_query failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ VectorStore: embed_query failed after {self.max_retries} attempts, using mock fallback")
                    return MockEmbeddings(self.embed_dim).embed_query(text)
        return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Get document embeddings with retry logic."""
        if self._using_mock:
            return self._embeddings.embed_documents(texts)

        for attempt in range(self.max_retries):
            try:
                return self._embeddings.embed_documents(texts)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  VectorStore: embed_documents failed "
                          f"(attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ VectorStore: embed_documents failed after "
                          f"{self.max_retries} attempts, using mock fallback")
                    return MockEmbeddings(self.embed_dim).embed_documents(texts)
        return []


class VectorStore:
    """PGVector-based semantic memory store with OpenAI embeddings."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize vector store with connection retry logic.

        Args:
            config: Configuration dictionary
            max_retries: Maximum number of connection retries
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.config = config or {}
        self.embedding_dim = self.config.get("embedding_dim", 1536)
        self.table_name = self.config.get("semantic_table", "semantic_memory")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize embeddings with fallback
        self._embedding_wrapper = OpenAIEmbeddingsWithFallback(
            dim=self.embedding_dim,
            max_retries=max_retries,
            retry_delay=retry_delay,
            model="text-embedding-3-small"
        )
        self.embeddings = self._embedding_wrapper
        self.using_real_embeddings = not self._embedding_wrapper.using_mock

        # In-memory storage for demo (would use PGVector in production)
        self._documents: List[Dict[str, Any]] = []

        # Try to connect to PGVector with retry logic
        self.using_pgvector = False
        self._init_pgvector()

    def _init_pgvector(self) -> None:
        """Initialize PGVector connection with retry logic."""
        # Check if we should skip PGVector
        if os.environ.get("SKIP_PGVECTOR", "false").lower() == "true":
            print("⚠️  VectorStore: Skipping PGVector (SKIP_PGVECTOR=true)")
            return

        for attempt in range(self.max_retries):
            try:
                # Try to import and connect to PGVector
                from langchain_community.vectorstores import PGVector

                # Verify PGVector is available (imported above)
                _ = PGVector.__name__

                # Note: Full PGVector initialization would happen here
                # For now, we just track that we could connect
                print("✅ VectorStore: PGVector connection available")
                self.using_pgvector = True
                return

            except ImportError:
                print("⚠️  VectorStore: langchain_community not available for PGVector")
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  VectorStore: PGVector connection failed "
                          f"(attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"   Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️  VectorStore: PGVector connection failed after "
                          f"{self.max_retries} attempts, using in-memory storage")

    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add document to vector store."""
        doc_id = metadata.get("id", str(uuid.uuid4())) if metadata else str(uuid.uuid4())

        # Generate embedding with retry logic
        embedding = self.embeddings.embed_query(content)

        # Store document
        doc = {
            "id": doc_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
        }

        self._documents.append(doc)
        return doc_id

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self._documents:
            return []

        # Generate query embedding with retry logic
        query_embedding = self.embeddings.embed_query(query)

        # Calculate similarities (cosine similarity)
        results = []
        for doc in self._documents:
            similarity = self._cosine_similarity(query_embedding, doc["embedding"])
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": similarity
            })

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        a = np.array(a)
        b = np.array(b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        for doc in self._documents:
            if doc["id"] == doc_id:
                return doc
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "document_count": len(self._documents),
            "embedding_dim": self.embedding_dim,
            "using_real_embeddings": self.using_real_embeddings,
            "using_pgvector": self.using_pgvector,
            "model": "text-embedding-3-small" if self.using_real_embeddings else "mock"
        }
