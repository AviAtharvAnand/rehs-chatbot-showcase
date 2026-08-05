# Your Chatbot Name

<!--
This becomes the body of your chatbot's page in the gallery.
About a page is right. Write it for a smart friend who doesn't code.
Delete these comments as you go.
-->

## What it does

Two paragraphs, plain language. What question does it answer, for whom, and why was that
annoying before? Name a real example question a user would type.

## How it works

Explain the pipeline in your own words, docs in, chunks, embeddings, retrieval, prompt,
answer with citations. A diagram helps:

```
docs ──► scrape + chunk ──► embed ──► vector DB
                                        │
                               search() │
                                        ▼
your question ──► prompt + retrieved passages ──► LLM ──► answer + citations
```

Say what you chose and why: chunk size, how many passages you retrieve, which model, how
the prompt is worded.

## How it's deployed

Your chatbot ran on Kubernetes, say so, in your own words. Which manifests did you
write (Deployment, Service, Ingress, PVC, ConfigMap)? How did your code get into the
pod? How did the vector database survive a restart? How did the token reach the pod
without being written into any file?

```
internet ──► Ingress (HTTPS) ──► Service ──► Deployment
                                              └── pod
                                                   ├── your code, from a ConfigMap
                                                   ├── settings, from a ConfigMap
                                                   ├── token, from a Secret
                                                   └── vector DB on a PersistentVolume
```

(Your page draws this automatically from the files in `k8s/`, this section is for the
parts a diagram can't show.)

And the honest part: what failed the first time you ran `kubectl apply`?
(`ImagePullBackOff`? `CrashLoopBackOff`? A PVC stuck `Pending`? Everyone hits these.)

## What I tried

The most interesting section, include what **didn't** work.

- **Tried:** … **Result:** … **Kept it?** yes/no
- **The bug that ate a day:** …
- **The thing that surprised me:** …

## Results

If you ran the eval, put the numbers in context: what did the failures have in common?
Which kind of question was hardest?

## What I'd do next

- …
- …
- …

## Running it yourself

Someone reading your page may want to try running your code. Tell them how:

```bash
pip install openai streamlit chromadb requests beautifulsoup4
export NRP_LLM_TOKEN=...        # your own token from https://nrp.ai/llmtoken
export NRP_LLM_BASE_URL=https://ellm.nrp-nautilus.io/v1
python src/ingest.py
streamlit run src/rag_app.py
```

## Credits

Built by <names> during the SDSC REHS <year> program. Thanks to <mentor> and the NRP team.
