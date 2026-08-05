# REHS Chatbot Showcase

**The AI chatbots built by high school students in the SDSC REHS program, one page per
chatbot, one page per student.**

**Gallery:** https://nrp-nautilus.github.io/rehs-chatbot-showcase/

Over eight weeks in the
[Research Experience for High School Students](https://education.sdsc.edu/studenttech/rehs/)
program at the [San Diego Supercomputer Center](https://www.sdsc.edu/), these students
built retrieval-augmented chatbots that answer questions about the
[National Research Platform](https://nrp.ai), grounded in real documentation, powered by
large language models served from NRP's own GPUs, and deployed them as Kubernetes
workloads on Nautilus, the NRP cluster.

---

## How it's organised

**Each student's chatbot is one folder at the top level of this repo:**

```
rehs-chatbot-showcase/
├── example-chatbot/      a complete example
├── <student-chatbot>/    one student, one folder
│   ├── bot.yaml              who built it and what it does
│   ├── README.md             the story, in their words
│   ├── screenshot.png        it, answering a real question
│   ├── src/                  the code they wrote
│   └── k8s/                  the Kubernetes manifests they applied
│
└── _pages/               the machinery that turns those folders into the website
```

From each folder the site generates a page for the chatbot and a page for each student
who built it. The Kubernetes section of every page is read **directly out of that
student's `k8s/` manifests**, the pod count from their Deployment, the volume size from
their PersistentVolumeClaim, the hostname from their Ingress, so what the page shows is
what they actually deployed.

Adding a chatbot is one pull request adding one folder. Merging it publishes the pages.

---

## Working on the site

```bash
make install     # the three Python packages this needs
make check       # validate every chatbot folder
make serve       # build and open http://localhost:8000
```

`_pages/template/` is the starting point for a new entry. `_pages/scripts/validate.py`
runs on every pull request; `_pages/scripts/build_site.py` generates `site/`, which is
git-ignored and published by GitHub Actions.

To turn the site on: **Settings -> Pages -> Source: GitHub Actions**.

---

## Ground rules

- **No secrets, ever.** No tokens, no `.env`, no `Secret` manifests, nothing sensitive in
  a screenshot. The automated check fails the pull request if it finds any. NRP tokens
  can be rotated at https://nrp.ai/llmtoken.
- **Credit is per person.** Every entry lists who built it and what each person did.

## Credits

Built by the students of the SDSC Research Experience for High School Students, on the
[National Research Platform](https://nrp.ai). Curriculum and starter code:
[rehs-chatbot-material](https://github.com/nrp-nautilus/rehs-chatbot-material).
License: [MIT](LICENSE).
