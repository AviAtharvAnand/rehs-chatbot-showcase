from src.embed.search import search


queries = [
    "How do I request a GPU pod?",
    "How do I run a Kubernetes job on Nautilus?",
    "How do I get access to NRP resources?"
]


for q in queries:

    print("\nQUESTION:")
    print(q)

    results = search(q, k=3)


    for r in results:
        print("\nTITLE:")
        print(r["title"])

        print("URL:")
        print(r["source_url"])

        print("SCORE:")
        print(r["score"])

        print("---")