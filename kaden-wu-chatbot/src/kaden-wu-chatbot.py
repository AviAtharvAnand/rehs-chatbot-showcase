import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import json
import subprocess
load_dotenv()

client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "/data/chroma_db"))

chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
coll = chroma_client.get_collection("nrp_docs")
def embed(text: str) -> list[float]:
    return client.embeddings.create(
        model="qwen3-embedding",
        input=[text]
    ).data[0].embedding

def search(query: str, k: int = 10) -> list[dict]:
    res = coll.query(
        query_embeddings=[embed(query)],
        n_results=min(k, coll.count())
    )

    return [
        {
            "text": d,
            "source_url": m["source_url"],
            "title": m["title"],
            "score": s
        }
        for d, m, s in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0]
        )
    ]
ALLOWED_VERBS = {"get", "describe", "top"}
ALLOWED_RESOURCES = {
    "pod", "pods",
    "svc", "service", "services",
    "deploy", "deployment", "deployments",
    "pvc", "nodes", "ingress", "events"
}

NAMESPACE = "rehs-2026-chatbot"


def search_nrp_docs(query: str) -> str:
    chunks = search(query, k=5)

    return json.dumps([
        {
            "title": c["title"],
            "text": c["text"],
            "source_url": c["source_url"]
        }
        for c in chunks
    ])

def run_kubectl(verb, resource):
    verb = verb.strip().split()[0]
    resource = resource.strip().split()[0]
    if verb not in ALLOWED_VERBS:
        return f"refused: verb '{verb}' not allowed (try get/describe/top)"
    if resource not in ALLOWED_RESOURCES:
        return f"refused: resource '{resource}' not allowed"
    import subprocess
    out = subprocess.run(
        ["kubectl", verb, resource, "-n", "rehs-2026-chatbot"],
        capture_output=True, text=True, timeout=30
    )
    return (out.stdout or out.stderr)[:1500]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_nrp_docs",
            "description": "Search NRP documentation for how-to and concept questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_kubectl",
            "description": "Run safe read-only kubectl commands for live cluster state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verb": {
                        "type": "string",
                        "enum": ["get", "describe", "top"]
                    },
                    "resource": {
                        "type": "string"
                    },
                },
                "required": ["verb", "resource"]
            }
        }
    }
]
st.title("🤖 NRP Helper")
st.caption("Your friendly guide to the National Research Platform")

if "history" not in st.session_state:
    st.session_state.history = []
if st.sidebar.button("Clear conversation"):
    st.session_state.history = []
    st.rerun()
for msg in st.session_state.history:
    if msg["role"] != "system":
        st.chat_message(msg["role"]).write(msg["content"])
temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.7, help=("Adjust the model's \"creativity\""))
user_input = st.chat_input("Ask about NRP...")
model = st.sidebar.selectbox("Model", ["gpt-oss", "qwen3-small", "gemma"], help=("Adjust what model is selected"))
reason = st.sidebar.selectbox("Reasoning", ["low", "medium", "high"], help=("Adjust how hard the model thinks when responding"))
max_tokens = st.sidebar.slider("Max output tokens", 50, 4000, 2000, help=("Adjust how long the models's response is") )
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    messages = [{"role": "system", "content": """You are a helpful NRP assistant. Use the tool search_nrp_docs for documentation questions. Use run_kubectl for questions about specific Kubernetes cluster related questions. The namespace is rehs-2026-chatbot. Use only available Kubernetes commands."""}] + st.session_state.history
    chunks_used = []
    with st.chat_message("assistant"):
        placeholder = st.empty()
        reply = ""
        reasoning = ""
        try:
          with st.spinner("Thinking..."):
            for _ in range(3):
                tool_response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    reasoning_effort=reason,
                    max_tokens=max_tokens,
                    tools=TOOLS,
                    tool_choice="auto"
                )
                tool_message = tool_response.choices[0].message
                if not tool_message.tool_calls:
                    break
                messages.append({
    			"role": "assistant",
    			"content": None,
    			"tool_calls": [
        			{
            			"id": call.id,
            			"type": "function",
            			"function": {
                			"name": call.function.name,
                			"arguments": call.function.arguments
            			}
        			}
        			for call in tool_message.tool_calls
    			]
})
                for call in tool_message.tool_calls:
                    tool_name = call.function.name
                    arguments = json.loads(call.function.arguments or "{}")
                    if tool_name == "search_nrp_docs":
                        chunks = search(arguments["query"], k=5)
                        chunks_used.extend(chunks)

                        tool_result = json.dumps([
                            {
                                "title": chunk["title"],
                                "text": chunk["text"],
                                "source_url": chunk["source_url"],
                                "distance": chunk["score"]
                            }
                            for chunk in chunks
                        ])
                    elif tool_name == "run_kubectl":
                        tool_result = run_kubectl(**arguments)
                    else:
                        tool_result = f"Unknown tool: {tool_name}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": str(tool_result)
                    })
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                reasoning_effort=reason,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content_piece = getattr(delta, "content", None)
                reasoning_piece = getattr(delta, "reasoning", None)

                if content_piece:
                    reply += content_piece
                    placeholder.markdown(reply)

                if reasoning_piece:
                    reasoning += reasoning_piece

        except Exception as e:
            reply = f"Error: {e}"
            st.error(reply)

        if chunks_used:
            with st.expander("Sources"):
                seen_urls = set()

                for chunk in chunks_used:
                    st.markdown(
                        f"- [{chunk['title']}]({chunk['source_url']}) "
                        f"*(distance: {chunk['score']:.3f})*"
                    )

    st.session_state.history.append({"role": "assistant", "content": reply})
