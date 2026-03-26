"""Memory Adapter Layer with LlamaIndex Integration.

Unified interface for episodic, semantic, and context memory.
Integrates LlamaIndex with PGVector and existing Knowledge Graph.
"""

import json
import uuid
import os
import random
import warnings
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.base.embeddings.base import BaseEmbedding


def get_db_config() -> Dict[str, Any]:
    """Get database configuration from environment or defaults."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "user": os.environ.get("POSTGRES_USER", "coe"),
        "password": os.environ.get("POSTGRES_PASSWORD", "coe_password"),
        "database": os.environ.get("POSTGRES_DB", "coe_memory"),
        "semantic_table": os.environ.get("SEMANTIC_TABLE", "semantic_memory"),
        "episodic_table": os.environ.get("EPISODIC_TABLE", "episodic_memory"),
        "embedding_dim": int(os.environ.get("EMBEDDING_DIM", "1536")),
    }


class MockEmbedding(BaseEmbedding):
    """Mock embedding model for testing without API calls.

    Generates deterministic embeddings based on text hash.
    Falls back to this when OPENAI_API_KEY is not available.
    """

    embed_dim: int = 1536

    def __init__(self, dim: int = 1536, **kwargs):
        super().__init__(**kwargs)
        self.embed_dim = dim

    def _get_text_embedding(self, text: str) -> List[float]:
        """Generate deterministic mock embedding based on text hash."""
        # Use hash to make embedding deterministic for same text
        seed = hash(text) % (2**31)
        rng = random.Random(seed)
        return [rng.uniform(-1, 1) for _ in range(self.embed_dim)]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for batch of texts."""
        return [self._get_text_embedding(text) for text in texts]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Async version of text embedding."""
        return self._get_text_embedding(text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Async version of batch text embeddings."""
        return self._get_text_embeddings(texts)

    def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query."""
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Async version of query embedding."""
        return self._get_query_embedding(query)


class OpenAIEmbeddingWithFallback:
    """OpenAI Embedding wrapper with automatic fallback to mock embeddings.

    Uses text-embedding-3-small with 1536 dimensions.
    Falls back to MockEmbedding if OPENAI_API_KEY is not set.
    """

    def __init__(self, dim: int = 1536, max_retries: int = 3, retry_delay: float = 1.0):
        self.embed_dim = dim
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._embed_model = None
        self._using_mock = False
        self._init_embedding_model()

    def _init_embedding_model(self):
        """Initialize embedding model with fallback logic."""
        api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            warnings.warn(
                "OPENAI_API_KEY not set. Using MockEmbedding as fallback. "
                "Set OPENAI_API_KEY environment variable for real embeddings.",
                UserWarning
            )
            self._embed_model = MockEmbedding(self.embed_dim)
            self._using_mock = True
            print("⚠️  Using MockEmbedding (OPENAI_API_KEY not set)")
            return

        # Try to initialize OpenAI embedding with retries
        for attempt in range(self.max_retries):
            try:
                from llama_index.embeddings.openai import OpenAIEmbedding
                self._embed_model = OpenAIEmbedding(
                    model="text-embedding-3-small",
                    api_key=api_key,
                    dimensions=self.embed_dim
                )
                self._using_mock = False
                print("✅ Using OpenAI text-embedding-3-small (1536 dims)")
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️  OpenAI embedding init failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"   Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    warnings.warn(
                        f"OpenAI embedding initialization failed after {self.max_retries} attempts: {e}. "
                        "Falling back to MockEmbedding.",
                        UserWarning
                    )

        # Fallback to mock
        self._embed_model = MockEmbedding(self.embed_dim)
        self._using_mock = True
        print("⚠️  Using MockEmbedding (OpenAI initialization failed)")

    @property
    def embed_model(self):
        """Get the underlying embedding model."""
        return self._embed_model

    @property
    def using_mock(self) -> bool:
        """Check if using mock embeddings."""
        return self._using_mock

    def get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding with retry logic."""
        if self._using_mock:
            return self._embed_model.get_text_embedding(text)

        for attempt in range(self.max_retries):
            try:
                return self._embed_model.get_text_embedding(text)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  Embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Embedding failed after {self.max_retries} attempts, using mock fallback")
                    return MockEmbedding(self.embed_dim).get_text_embedding(text)
        return []

    def get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get batch text embeddings with retry logic."""
        if self._using_mock:
            return self._embed_model.get_text_embeddings(texts)

        for attempt in range(self.max_retries):
            try:
                return self._embed_model.get_text_embeddings(texts)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️  Batch embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Batch embedding failed after {self.max_retries} attempts, using mock fallback")
                    return MockEmbedding(self.embed_dim).get_text_embeddings(texts)
        return []

    def get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding with retry logic."""
        return self.get_text_embedding(query)


class MemoryAdapter:
    """Unified memory interface for LangGraph integration with LlamaIndex."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, use_mock_embeddings: bool = False):
        """Initialize memory stores with LlamaIndex."""
        self.config = config or get_db_config()
        self.use_mock = use_mock_embeddings or os.environ.get("USE_MOCK_EMBEDDINGS", "false").lower() == "true"

        # Initialize embedding model with fallback support
        if self.use_mock:
            self.embed_model = MockEmbedding(self.config["embedding_dim"])
            self.using_real_embeddings = False
            print("✓ Using mock embeddings for testing")
        else:
            # Use wrapper with automatic fallback
            self._embedding_wrapper = OpenAIEmbeddingWithFallback(
                dim=self.config["embedding_dim"],
                max_retries=3,
                retry_delay=1.0
            )
            self.embed_model = self._embedding_wrapper.embed_model
            self.using_real_embeddings = not self._embedding_wrapper.using_mock

        Settings.embed_model = self.embed_model

        # Node parser for chunking
        self.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50
        )

        # In-memory storage for demo (will use PGVector when DB is available)
        self._documents: List[Document] = []
        self._episodes: List[Dict[str, Any]] = []
        self._index: Optional[VectorStoreIndex] = None
        self.using_pgvector = False

        # Try to connect to PGVector if available
        self._init_vector_store()

    def _init_vector_store(self) -> None:
        """Initialize vector store connection."""
        try:
            from llama_index.vector_stores.postgres import PGVectorStore

            vector_store = PGVectorStore.from_params(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                table_name=self.config["semantic_table"],
                embed_dim=self.config["embedding_dim"],
            )

            self._index = VectorStoreIndex.from_vector_store(vector_store)
            self.using_pgvector = True
            print("✓ Connected to PGVector store")
        except Exception as e:
            self.using_pgvector = False
            print(f"⚠ PGVector not available ({str(e)[:50]}...), using in-memory storage")
            self._index = None

    def store_episode(self, task_data: Dict[str, Any]) -> str:
        """Store episodic memory of task execution."""
        episode_id = str(uuid.uuid4())

        episode = {
            "id": episode_id,
            "task_id": task_data["task_id"],
            "input": task_data["input"],
            "plan": json.dumps(task_data.get("plan", [])),
            "result": task_data["output"],
            "steps": json.dumps(task_data.get("steps", [])),
            "success": task_data.get("success", True),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "source": "task_execution",
                "type": "episode"
            }
        }

        # Store in memory
        self._episodes.append(episode)

        # Try to store in PostgreSQL if available
        self._store_episode_pg(episode)

        return episode_id

    def _store_episode_pg(self, episode: Dict[str, Any]) -> None:
        """Store episode in PostgreSQL."""
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"]
            )

            with conn.cursor() as cur:
                # Create table if not exists
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.config['episodic_table']} (
                        id UUID PRIMARY KEY,
                        task_id TEXT,
                        input TEXT,
                        plan TEXT,
                        result TEXT,
                        steps TEXT,
                        success BOOLEAN,
                        created_at TIMESTAMP,
                        metadata JSONB
                    )
                """)

                cur.execute(f"""
                    INSERT INTO {self.config['episodic_table']}
                    (id, task_id, input, plan, result, steps, success, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (
                    episode["id"],
                    episode["task_id"],
                    episode["input"],
                    episode["plan"],
                    episode["result"],
                    episode["steps"],
                    episode["success"],
                    episode["created_at"],
                    json.dumps(episode["metadata"])
                ))

                conn.commit()
                print(f"✓ Episode stored in PostgreSQL: {episode['id'][:8]}...")
        except Exception as e:
            print(f"⚠ Could not store episode in PostgreSQL: {str(e)[:60]}...")

    def store_knowledge(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store semantic knowledge in vector store."""
        knowledge_id = str(uuid.uuid4())

        doc_metadata = metadata or {}
        doc_metadata["id"] = knowledge_id
        doc_metadata["created_at"] = datetime.now(timezone.utc).isoformat()

        # Create LlamaIndex document
        doc = Document(text=content, metadata=doc_metadata)

        # Store in memory
        self._documents.append(doc)

        if self.using_pgvector and self._index and not self.use_mock:
            # Store in PGVector
            self._index.insert(doc)
        else:
            # Rebuild in-memory index
            self._rebuild_index()

        return knowledge_id

    def _rebuild_index(self) -> None:
        """Rebuild the in-memory vector index."""
        if self._documents:
            # Build index manually with our embedding model
            from llama_index.core.schema import TextNode

            nodes = []
            for doc in self._documents:
                embedding = self.embed_model.get_text_embedding(doc.text)
                node = TextNode(
                    text=doc.text,
                    metadata=doc.metadata,
                    embedding=embedding
                )
                nodes.append(node)

            self._index = VectorStoreIndex(nodes)

    def retrieve_context(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve relevant context from semantic memory using LlamaIndex."""
        if not self._documents:
            return []

        if self._index and self.using_pgvector and not self.use_mock:
            # Use LlamaIndex retriever with PGVector
            retriever = self._index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            return [node.text for node in nodes]
        else:
            # Use in-memory retrieval with cosine similarity
            return self._retrieve_in_memory(query, top_k)

    def _retrieve_in_memory(self, query: str, top_k: int = 5) -> List[str]:
        """Fallback retrieval using embedding similarity."""
        if not self._documents:
            return []

        # Get query embedding
        query_embedding = self.embed_model.get_text_embedding(query)

        # Calculate similarities
        results = []
        for doc in self._documents:
            doc_embedding = self.embed_model.get_text_embedding(doc.text)
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            results.append((doc.text, similarity))

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return [text for text, _ in results[:top_k]]

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

    def retrieve_episodes(self, task_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve episodic memories."""
        # Try PostgreSQL first
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"]
            )

            with conn.cursor() as cur:
                if task_id:
                    cur.execute(f"""
                        SELECT id, task_id, input, plan, result, steps, success, created_at, metadata
                        FROM {self.config['episodic_table']}
                        WHERE task_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (task_id, limit))
                else:
                    cur.execute(f"""
                        SELECT id, task_id, input, plan, result, steps, success, created_at, metadata
                        FROM {self.config['episodic_table']}
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))

                rows = cur.fetchall()
                conn.close()

                if rows:
                    return [
                        {
                            "id": row[0],
                            "task_id": row[1],
                            "input": row[2],
                            "plan": row[3],
                            "result": row[4],
                            "steps": row[5],
                            "success": row[6],
                            "created_at": row[7],
                            "metadata": row[8] if isinstance(row[8], dict) else json.loads(row[8]) if row[8] else {}
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"⚠ PostgreSQL query failed: {str(e)[:60]}..., using in-memory")

        # Fallback to in-memory
        results = self._episodes.copy()

        if task_id:
            results = [e for e in results if e.get("task_id") == task_id]

        # Sort by created_at descending
        results = sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

        return results[:limit]

    def summarize_and_store(self, task_data: Dict[str, Any]) -> str:
        """Summarize task and store as knowledge."""
        # Generate summary from task data
        summary = f"Task '{task_data['input'][:100]}' completed with result: {task_data['output'][:100]}"

        return self.store_knowledge(summary, {
            "source": "task_summary",
            "task_id": task_data["task_id"],
            "type": "summary",
            "success": task_data.get("success", True)
        })

    def hybrid_retrieval(self, query: str, top_k: int = 5) -> Dict[str, List[Any]]:
        """Hybrid retrieval from vector store and knowledge graph."""
        # Vector results
        vector_results = self.retrieve_context(query, top_k=top_k)

        # Would also query knowledge graph here
        kg_results = []

        return {
            "vector": vector_results,
            "knowledge_graph": kg_results
        }

    def post_task_learning(self, task_data: Dict[str, Any]) -> Dict[str, str]:
        """Execute learning loop: store episode → summarize → store knowledge."""
        # Step 1: Store episode
        episode_id = self.store_episode(task_data)

        # Step 2: Summarize and store knowledge
        knowledge_id = self.summarize_and_store(task_data)

        return {
            "episode_id": episode_id,
            "knowledge_id": knowledge_id
        }


# Legacy compatibility
