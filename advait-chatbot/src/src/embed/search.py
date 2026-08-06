import os

import chromadb
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


TOKEN = os.getenv("NRP_LLM_TOKEN")
BASE_URL = os.getenv("NRP_LLM_BASE_URL")


client = OpenAI(
    api_key=TOKEN,
    base_url=BASE_URL
)


# --------------------------
# Open Chroma database
# --------------------------

chroma = chromadb.PersistentClient(
    path="chroma_db"
)

collection = chroma.get_collection(
    "nrp_docs"
)


# --------------------------
# Embedding helper
# --------------------------

def embed(text: str):

    response = client.embeddings.create(
        model="qwen3-embedding",
        input=[text]
    )

    return response.data[0].embedding


# --------------------------
# Search
# --------------------------

def search(query: str, k: int = 5):

    query_embedding = embed(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    chunks = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        chunks.append(

            {

                "text": doc,

                "title": metadata["title"],

                "source_url": metadata["source_url"],

                "score": float(distance)

            }

        )

    chunks.sort(
        key=lambda x: x["score"]
    )

    return [
        c for c in chunks
        if c["score"] < 0.7
    ]