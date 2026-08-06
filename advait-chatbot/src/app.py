import streamlit as st

from src.embed.rag import answer_question


# -------------------------
# Page config
# -------------------------

st.set_page_config(
    page_title="NRP Helper",
    page_icon="🤖",
    layout="centered"
)


# -------------------------
# Custom CSS
# -------------------------

st.markdown(
    """
    <style>

    .block-container {
        max-width: 900px;
        padding-top: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# -------------------------
# Sidebar
# -------------------------

with st.sidebar:

    st.title("🤖 NRP Helper")

    st.caption(
        "AI assistant for NRP documentation"
    )


    st.divider()


    if st.button("🗑️ Clear Chat"):

        st.session_state.messages = []

        st.rerun()


    st.subheader("Settings")


    response_style = st.selectbox(
        "Response style",
        [
            "Concise",
            "Detailed",
            "Tutorial"
        ]
    )


    num_chunks = st.slider(
        "Documentation sections",
        min_value=3,
        max_value=10,
        value=5
    )


    show_sources = st.checkbox(
        "Show sources",
        value=True
    )


    st.divider()


    st.subheader("Example questions")


    example_questions = [
        "How do I request a GPU pod?",
        "How do I deploy a Kubernetes job?",
        "How does storage work?"
    ]


    for question in example_questions:

        if st.button(question):

            st.session_state.prompt = question



# -------------------------
# Main page
# -------------------------

st.title("🤖 NRP Helper")

st.caption(
    "Your AI assistant for the National Research Platform documentation"
)



# -------------------------
# Welcome screen
# -------------------------

if "messages" not in st.session_state:

    st.session_state.messages = []


if len(st.session_state.messages) == 0:

    st.markdown(
        """
        ### Welcome!

        Ask questions about:

        - 🚀 GPU resources
        - ☸️ Kubernetes
        - 💾 Storage
        - 🌐 Networking
        - 🤖 LLM services


        Try asking:

        **How do I request a GPU pod?**
        """
    )



# -------------------------
# Display chat history
# -------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )



# -------------------------
# Input handling
# -------------------------

prompt = st.chat_input(
    "Ask about NRP..."
)


# If example button clicked

if "prompt" in st.session_state:

    prompt = st.session_state.prompt

    del st.session_state.prompt



if prompt:



    with st.chat_message("user"):

        st.markdown(prompt)



    with st.chat_message("assistant"):


        status = st.status(
            "🔎 Searching NRP documentation...",
            expanded=False
        )


        result = answer_question(
            prompt,
            history=st.session_state.messages[-10:],
            style=response_style,
            k=num_chunks
        )       

        status.update(
            label="🤖 Generating response...",
            state="running"
        )


        answer = st.write_stream(
            result["answer"]
        )

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


        status.update(
            label="Complete",
            state="complete"
        )



        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer
            }
        )



        # -------------------------
        # Sources
        # -------------------------

        if show_sources:

            with st.expander("📚 Sources"):

                seen = set()

                source_number = 1

                for chunk in result["chunks"]:

                    url = chunk["source_url"]

                    if url in seen:
                        continue

                    seen.add(url)


                    st.markdown(
                        f"""
                        **{source_number}. {chunk['title']}**

                        📖 NRP Documentation

                        🔗 {url}

                        ---
                        """
                    )

                    source_number += 1