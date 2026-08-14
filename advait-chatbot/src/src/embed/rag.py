import os

from dotenv import load_dotenv
from openai import OpenAI

from .search import search


load_dotenv()

TOKEN = os.getenv("NRP_LLM_TOKEN")
BASE_URL = os.getenv("NRP_LLM_BASE_URL")


client = OpenAI(
    api_key=TOKEN,
    base_url=BASE_URL
)


def answer_question(
    query: str,
    history=[],
    style="Concise",
    k=7
):

    chunks = search(query, k=k)

    context = "\n\n--------------------\n\n".join(

        f"""
TITLE:
{c["title"]}

URL:
{c["source_url"]}

CONTENT:
{c["text"]}
"""

        for c in chunks

    )


    system_prompt = """
You are an expert assistant for the National Research Platform (NRP).

Your job is to answer ONLY using the documentation provided.

Rules:

- Never invent information.
- If the documentation does not answer the question, explicitly say so.
- Prefer concise but complete answers.
- Use markdown formatting.
"""


    if style == "Concise":

        system_prompt += """
Keep answers short and direct.
"""


    elif style == "Detailed":

        system_prompt += """
Provide detailed explanations and context.
"""


    elif style == "Tutorial":

        system_prompt += """
Explain step-by-step like teaching a beginner.
"""


    user_prompt = f"""
Documentation:

{context}


Question:

{query}


Answer using only the documentation above.
"""


    def stream_response():
        # 1. Build the full messages list first
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # Add previous conversation history
        for message in history:
            messages.append(
                {
                    "role": message["role"],
                    "content": message["content"]
                }
            )

        # Add current question
        messages.append(
            {
                "role": "user",
                "content": user_prompt
            }
        )

        # 2. Pass the constructed list to the API call
        response = client.chat.completions.create(
            model="qwen3-small",
            temperature=0.1,
            stream=True,
            messages=messages
        )

        for chunk in response:

            if not chunk.choices:
                continue

            token = chunk.choices[0].delta.content

            if token:
                yield token


    return {

        "answer": stream_response(),

        "chunks": chunks

    }