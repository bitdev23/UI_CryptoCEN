"""RAG system using ChromaDB and sentence-transformers embeddings."""
from typing import List, Tuple, Optional
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from pathlib import Path
import logging

logger = logging.getLogger("valtrilabs.rag")


class RAGStore:
    def __init__(self, persist_dir: str = "data/chroma_db"):
        self.persist_dir = persist_dir
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        try:
            # Use modern ChromaDB PersistentClient API
            self.client = chromadb.PersistentClient(path=self.persist_dir)
        except Exception:
            logger.exception("Failed to init ChromaDB client")
            raise
        self.collection = None
        self.model = None

    def _get_model(self):
        if self.model is None:
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self.model

    def build_from_documents(self, docs: List[Tuple[str, str]], collection_name: str = "valtrilabs") -> None:
        """docs: list of (source, text)"""
        if not docs:
            logger.warning("No documents provided to build RAG store")
            return
        try:
            self.collection = self.client.get_or_create_collection(name=collection_name)
            model = self._get_model()
            ids = []
            metadatas = []
            embeddings = []
            documents = []
            for i, (src, text) in enumerate(docs):
                emb = model.encode(text)
                ids.append(f"doc_{i}")
                metadatas.append({"source": src})
                embeddings.append(emb.tolist())
                documents.append(text)
            self.collection.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
            logger.info("Built vector store with %d documents", len(docs))
        except Exception:
            logger.exception("Failed to build vector store")

    def persist(self) -> None:
        # PersistentClient auto-persists; this is a no-op but kept for compatibility
        logger.info("ChromaDB persisted to %s (automatic)", self.persist_dir)

    def is_built(self) -> bool:
        """Check if the RAG model has been trained with documents"""
        try:
            if self.collection is None:
                self.collection = self.client.get_or_create_collection(name="valtrilabs")
            # Check if collection has any documents
            count = self.collection.count()
            return count > 0
        except Exception:
            logger.exception("Failed to check if RAG is built")
            return False

    def get_document_count(self) -> int:
        """Get the number of documents in the collection"""
        try:
            if self.collection is None:
                self.collection = self.client.get_or_create_collection(name="valtrilabs")
            return self.collection.count()
        except Exception:
            logger.exception("Failed to get document count")
            return 0

    def similarity_search(self, query: str, k: int = 4) -> List[dict]:
        try:
            model = self._get_model()
            qemb = model.encode(query).tolist()
            if self.collection is None:
                self.collection = self.client.get_or_create_collection(name="valtrilabs")
            res = self.collection.query(query_embeddings=[qemb], n_results=k, include=['documents', 'metadatas', 'distances'])
            docs = []
            if res.get('documents') and len(res['documents']) > 0:
                for docs_list, metas_list, dists in zip(res.get('documents', []), res.get('metadatas', []), res.get('distances', [])):
                    for doc, meta, dist in zip(docs_list, metas_list, dists):
                        docs.append({"document": doc, "metadata": meta, "distance": dist})
            return docs
        except Exception:
            logger.exception("Similarity search failed")
            return []


if __name__ == "__main__":
    import dotenv, logging
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    store = RAGStore()
    print("RAGStore initialized")
