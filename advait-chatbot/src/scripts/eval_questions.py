from src.embed.search import search


questions = [
    "How do I request a GPU pod?",
    "How do I run a Kubernetes job?",
    "How do I create a namespace?",
    "How do I connect to Nautilus?",
    "How do I install kubectl?",
    "How do I request storage?",
    "How do I use GPUs with jobs?",
    "How do I delete a pod?",
    "What are the CPU limits?",
    "How do I access NRP resources?"
]


for q in questions:

    print("\n====================")
    print("QUESTION:")
    print(q)

    results = search(q, k=3)

    for r in results:

        print("\nTITLE:")
        print(r["title"])

        print("URL:")
        print(r["source_url"])

        print("SCORE:")
        print(r["score"])