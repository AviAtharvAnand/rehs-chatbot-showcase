# Put your chatbot's source code here

Delete this file once you've added it.

Everything you wrote: the app, the ingest script, the retrieval code, any helpers.
Layout is up to you, however your project was organised is fine:

```
src/
├── rag_app.py     the chatbot interface
├── ingest.py      reads the docs, chunks them, fills the vector database
└── ...            anything else you wrote
```

This is the evidence that you built it. Someone looking at your page, an admissions
reader, an interviewer, a future employer, can click through and see your actual code.
That's worth more than any description of it.

## What not to include

- **No `.env` file** and no tokens anywhere in the code. If a token is hard-coded in
  your source, delete it and rotate it at https://nrp.ai/llmtoken before you commit.
  The automated check looks for this.
- **No vector database** (`chroma_db/`) and no scraped documentation dumps, they're
  large, and they get rebuilt from your ingest script anyway.
- **No `__pycache__/`, no `.venv/`.**

Messy code is fine. Half-finished code is fine. Code with a comment saying
`# TODO: this is a hack, it works though` is genuinely fine, real repositories look
like that. Don't clean it up so much that it stops being yours.
