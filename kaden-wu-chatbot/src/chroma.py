import os
import json
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TOKEN = os.getenv("NRP_LLM_TOKEN")
BASE_URL = os.getenv("NRP_LLM_BASE_URL")

if not TOKEN:
    raise ValueError("NRP_LLM_TOKEN was not found")

if not BASE_URL:
    raise ValueError("NRP_LLM_BASE_URL was not found")

client = OpenAI(
    api_key=TOKEN,
    base_url=BASE_URL
)

PROJECT_ROOT = Path(__file__).resolve().parent
CHUNKS_FOLDER = PROJECT_ROOT / "data" / "chunks"
CHROMA_FOLDER = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "nrp_docs"
EMBEDDING_MODEL = "qwen3-embedding"

def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text]
    )
    return response.data[0].embedding

def embed_many(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]

def load_chunks() -> list[dict]:
    chunks = []

    for file_path in sorted(CHUNKS_FOLDER.glob("*.json")):
        with file_path.open("r", encoding="utf-8") as file:
            chunk = json.load(file)

        if not chunk.get("id"):
            continue

        if not chunk.get("text", "").strip():
            continue

        chunks.append(chunk)

    return chunks

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_FOLDER)
)

coll = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

def index_chunks(chunks: list[dict], batch_size: int = 32) -> None:
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        ids = [chunk["id"] for chunk in batch]
        documents = [chunk["text"] for chunk in batch]
        embeddings = embed_many(documents)

        metadatas = [
            {
                "source_url": chunk.get("source_url", ""),
                "title": chunk.get("title", ""),
                "source_path": chunk.get("source_path", ""),
                "chunk_index": chunk.get("chunk_index", 0)
            }
            for chunk in batch
        ]

        coll.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        print(f"Indexed {min(start + batch_size, len(chunks))}/{len(chunks)}")

def search(query: str, k: int = 5) -> list[dict]:
    if coll.count() == 0:
        return []

    k = min(k, coll.count())

    results = coll.query(
        query_embeddings=[embed(query)],
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )

    output = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        output.append(
            {
                "text": document,
                "source_url": metadata.get("source_url", ""),
                "title": metadata.get("title", ""),
                "source_path": metadata.get("source_path", ""),
                "chunk_index": metadata.get("chunk_index", 0),
                "score": 1 - distance,
                "distance": distance
            }
        )

    return output

def run_tests() -> None:
    test_queries = [
        "How do I log into the NRP Nautilus cluster?",
        "How can I request a GPU in Kubernetes?",
        "How do I create a Kubernetes pod?",
        "How do I use persistent storage on NRP?",
        "How do I transfer files to Nautilus?",
        "What resource limits should I set for a job?",
        "How do I run a Jupyter notebook on NRP?",
        "How do I troubleshoot a pod that is pending?",
        "How do I access an interactive shell in a container?",
        "What are the rules and policies for using NRP?"
    ]

    for query in test_queries:
        print("\n" + "=" * 100)
        print(f"QUERY: {query}")

        results = search(query, k=3)

        for index, result in enumerate(results, start=1):
            print(f"\nRESULT {index}")
            print(f"Title: {result['title']}")
            print(f"Source: {result['source_url']}")
            print(f"Similarity: {result['score']:.4f}")
            print(result["text"][:500].replace("\n", " "))

if __name__ == "__main__":
    chunks = load_chunks()

    if not chunks:
        raise ValueError(
            f"No JSON chunks were found in {CHUNKS_FOLDER}. "
            "Run scripts/ingest.py first."
        )

    print(f"Loaded {len(chunks)} chunks")
    index_chunks(chunks)
    print(f"Collection contains {coll.count()} chunks")
    run_tests()
