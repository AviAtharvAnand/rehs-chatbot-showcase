import os
import json
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
# Load chunks
# --------------------------

chunks = []

for filename in sorted(os.listdir("data/chunks")):

    if filename.endswith(".json"):

        with open(
            os.path.join("data/chunks", filename)
        ) as f:

            chunks.append(json.load(f))

print(f"Loaded {len(chunks)} chunks")

# --------------------------
# Create Chroma database
# --------------------------

chroma = chromadb.PersistentClient(
    path="chroma_db"
)

try:

    chroma.delete_collection("nrp_docs")
    print("Deleted old collection")

except Exception:

    pass

collection = chroma.create_collection(
    "nrp_docs"
)

# --------------------------
# Embed helper
# --------------------------

def embed(texts):

    response = client.embeddings.create(
        model="qwen3-embedding",
        input=texts
    )

    return [
        item.embedding
        for item in response.data
    ]

# --------------------------
# Batch embedding
# --------------------------

BATCH_SIZE = 25

for start in range(0, len(chunks), BATCH_SIZE):

    batch = chunks[start:start+BATCH_SIZE]

    print(
        f"Embedding {start} / {len(chunks)}"
    )

    embeddings = embed(
        [c["text"] for c in batch]
    )

    collection.add(

        ids=[
            c["id"]
            for c in batch
        ],

        documents=[
            c["text"]
            for c in batch
        ],

        embeddings=embeddings,

        metadatas=[

            {

                "source_url": c["source_url"],
                "title": c["title"]

            }

            for c in batch

        ]

    )

print("Finished embedding!")