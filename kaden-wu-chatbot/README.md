# A Brief Chatbot README
## What it does
This chatbot uses retrieval-augmented generation (RAG) to provide enhanced responses to user queries about a specific set of documentation (e.g. NRP). It can also perform Kubernetes tool calls in a namespace. 
## How it works
First, the chatbot looks at a documentation and indexes chunks that it will reference later. Then, the embeddings of these chunks are extracted and the closest ones to the query are used as context. Finally, the robot builds its response given the context from the embeddings.  
The chatbot also has the ability to run live Kubernetes commands from a select list of read-only commands.
## How it's deployed
The chatbot runs as a Kubernetes deployment inside a service. It also uses ingress in order to have a public URL, and uses role based access control (RBAC) to run its Kubernetes commands. Permissions are very important in Kubernetes, as without the right permissions, you are not allowed to execute system commands.
## What I tried
I tried expanding the UI in order to make the user interface more appealing, and I also added history so that the chatbot remembers previous instructions. 
## What I'd do next
- Expand the chatbot to have a larger selection of LLMs.
- Add more documentation for the chatbot to reference.
- Use a better embedding model for better chunk retrieval. 
