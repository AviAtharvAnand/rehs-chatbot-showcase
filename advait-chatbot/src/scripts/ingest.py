import os
import re
import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag

from langchain_text_splitters import RecursiveCharacterTextSplitter

START_URL = "https://nrp.ai/documentation/"
OUTPUT = "data/chunks"

visited = set()
chunks = []


splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    separators=[
        "\n## ",
        "\n### ",
        "\n\n",
        "\n",
        ". ",
        " "
    ]
)


os.makedirs(
    OUTPUT,
    exist_ok=True
)


# -------------------------
# Normalize URLs
# -------------------------

def normalize_url(url):

    url = url.split("#")[0]

    url = url.rstrip("/")

    return url


def clean_text(text):

    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)

    return text.strip()

# -------------------------
# Scrape one page
# -------------------------

def scrape(url):

    url = normalize_url(url)

    if url in visited:
        return []

    visited.add(url)

    print("Scraping:", url)

    try:

        r = requests.get(
            url,
            timeout=10
        )

        if r.status_code != 200:
            return []

    except Exception:

        return []


    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )


    # remove useless elements
    for tag in soup([
        "nav",
        "footer",
        "script",
        "style",
        "aside",
        "noscript",
        "svg"
    ]):
        tag.decompose()


    text = soup.get_text(
        separator="\n"
    )

    text = clean_text(text)


    page_chunks = splitter.split_text(text)

    results = []


    safe_id = (

        url
        .replace("https://", "")
        .replace("/", "_")

    )


    for i, chunk in enumerate(page_chunks):

        results.append(

            {

                "id": f"{safe_id}_{i}",

                "source_url": url,

                "title":
                    soup.title.get_text(strip=True)
                    if soup.title
                    else url,
                "text": chunk

            }

        )


    return results


# -------------------------
# Crawl recursively
# -------------------------

def crawl(url, depth=0, max_depth=3):

    if depth > max_depth:
        return

    url, _ = urldefrag(url)

    if url.endswith("/"):
        url = url[:-1]

    if url in visited:
        return

    new_chunks = scrape(url)

    chunks.extend(new_chunks)

    try:

        r = requests.get(url, timeout=10)

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        for link in soup.find_all("a"):

            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(url, href)

            full_url, _ = urldefrag(full_url)

            if full_url.endswith("/"):
                full_url = full_url[:-1]

            if not full_url.startswith(
                "https://nrp.ai/documentation"
            ):
                continue

            if any(
                full_url.endswith(ext)
                for ext in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".pdf",
                    ".zip"
                ]
            ):
                continue

            crawl(
                full_url,
                depth + 1,
                max_depth
            )

    except Exception:

        pass


# -------------------------
# Run crawl
# -------------------------

crawl(START_URL)


print(
    "Total chunks:",
    len(chunks)
)


# -------------------------
# Save chunks
# -------------------------

for filename in os.listdir(OUTPUT):

    if filename.endswith(".json"):

        os.remove(
            os.path.join(
                OUTPUT,
                filename
            )
        )

print("Removing duplicate chunks...")

seen = set()
unique = []

for chunk in chunks:

    key = (
        chunk["title"],
        chunk["text"][:300]
    )

    if key not in seen:

        seen.add(key)
        unique.append(chunk)

chunks = unique

print("Final chunks:", len(chunks))

for i, chunk in enumerate(chunks):

    with open(

        f"{OUTPUT}/{i}.json",

        "w"

    ) as f:

        json.dump(
            chunk,
            f,
            indent=2
        )


print("Done")