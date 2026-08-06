# Advait's NRP Documentation Chatbot

## What it does

NRP Helper is an AI-powered documentation assistant that answers questions about the National Research Platform (NRP) using information from official NRP documentation.

Unlike a normal chatbot that relies only on a language model's existing knowledge, NRP Helper uses Retrieval-Augmented Generation (RAG). When a user asks a question, the system first searches through a database containing embedded NRP documentation, retrieves the most relevant sections, and then uses those sections to generate a grounded answer.

Example question:

> How do I request a GPU pod?

The chatbot retrieves the relevant NRP documentation and generates an answer explaining the required Kubernetes configuration while providing the original documentation sources.

---

# How it works

The chatbot consists of three major stages.

## 1. Documentation ingestion

The ingestion pipeline collects information from the NRP documentation website.

The pipeline:

- Crawls NRP documentation pages
- Removes unnecessary webpage elements
- Cleans and processes extracted text
- Splits documents into smaller chunks
- Stores the chunks for embedding

Splitting documentation into smaller sections allows the system to efficiently search through a large documentation collection.

---

## 2. Embeddings and vector search

Each documentation chunk is converted into a numerical embedding using the `qwen3-embedding` model.

These embeddings are stored in ChromaDB, a vector database.

When a user asks a question:

1. The question is converted into an embedding.
2. ChromaDB searches for the most similar documentation chunks.
3. The most relevant sections are returned to the language model.

The retrieval process allows the chatbot to ground its answers in official NRP documentation instead of relying only on general model knowledge.

---

## 3. Answer generation

The retrieved documentation is inserted into a prompt sent to the NRP LLM API.

The model is instructed to:

- Only use the provided documentation
- Avoid unsupported claims
- Explain concepts clearly
- Provide relevant sources

The response is streamed token-by-token through the Streamlit interface, creating a more interactive user experience.

---

# Deployment

The chatbot is deployed as a Kubernetes workload on the NRP Nautilus cluster.

The deployment includes:

- Kubernetes Deployment for running the Streamlit application
- Service and Ingress for accessing the application
- PersistentVolumeClaim for storing the ChromaDB database
- ConfigMap for application configuration
- Kubernetes Secret for securely providing API credentials

The overall architecture:

NRP Documentation  
↓  
Documentation Ingestion Pipeline  
↓  
Text Chunks  
↓  
Embeddings  
↓  
ChromaDB Vector Database  
↓  
Streamlit Web Interface  
↓  
LLM Generated Response

---

# Challenges and what I learned

## Improving retrieval quality

One of the biggest challenges was improving the quality of retrieved documentation.

I experimented with:

- Chunk size
- Chunk overlap
- Number of retrieved sections
- Similarity filtering

Small changes to retrieval parameters significantly affected the quality of generated answers.

---

## Deploying an AI application with Kubernetes

Moving from a local Python application to a Kubernetes deployment introduced new challenges:

- Managing persistent storage
- Updating Docker images
- Handling environment variables securely
- Debugging rollout failures
- Maintaining application state

This helped me understand how real AI applications are deployed and maintained.

---

## Improving user experience

The final interface includes:

- Streaming responses
- Adjustable response styles
- Configurable retrieval depth
- Source citations
- Example questions

These features make the chatbot easier to use and more transparent.

---

# Results

The chatbot successfully answers technical questions about NRP documentation while providing the sources used to generate each response.

Testing focused on:

- Retrieval quality
- Answer correctness
- Preventing unsupported responses
- Overall usability

The chatbot performs best when the requested information exists clearly within the NRP documentation.

Limitations occur when:

- The documentation does not contain the requested information
- Multiple pages discuss similar topics
- A question requires information outside the documentation

---

# Future improvements

Potential future improvements include:

- Adding multi-turn conversation memory
- Improving retrieval using hybrid keyword and vector search
- Creating automated evaluation benchmarks
- Supporting additional documentation sources
- Adding user feedback mechanisms
