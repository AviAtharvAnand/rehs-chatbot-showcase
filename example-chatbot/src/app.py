"""Placeholder app, the simplest thing that shows the shape of a RAG chatbot.

Your src/ should contain the code you actually wrote, however you wrote it.
"""

import os

import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["NRP_LLM_TOKEN"],
    base_url=os.environ["NRP_LLM_BASE_URL"],
)


def search(question):
    """Find documentation passages related to the question. (Yours does the real work.)"""
    return []


st.title("Example Chatbot")

question = st.chat_input("Ask a question...")
if question:
    st.chat_message("user").write(question)

    passages = search(question)
    prompt = f"Answer the question using these passages.\n\n{passages}\n\n{question}"

    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "gpt-oss"),
        messages=[{"role": "user", "content": prompt}],
    )
    st.chat_message("assistant").write(response.choices[0].message.content)
