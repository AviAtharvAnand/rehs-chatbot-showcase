from src.embed.rag import answer_question


questions = [

"How do I request a GPU pod?",

"How do I run a Kubernetes job?",

"How do I get access to NRP?"

]


for q in questions:

    print("\nQUESTION:")
    print(q)


    result = answer_question(q)


    print("\nANSWER:")
    print(result["answer"])


    print("\nSOURCES:")

    for c in result["chunks"]:

        print(
            "-",
            c["title"],
            c["source_url"]
        )
