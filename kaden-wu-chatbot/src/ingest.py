from pathlib import Path
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCS_FOLDER = Path("documentation")
OUTPUT_FOLDER = Path("data/chunks")
BASE_URL = "https://nrp.ai/documentation/"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400,
    separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""]
)

for old_file in OUTPUT_FOLDER.glob("*.json"):
    old_file.unlink()

chunk_count = 0

for file_path in DOCS_FOLDER.rglob("*"):
    if file_path.suffix.lower() not in {".md", ".mdx"}:
        continue

    text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        continue

    chunks = splitter.split_text(text)

    for chunk_index, chunk_text in enumerate(chunks):
        chunk = {
            "id": f"chunk-{chunk_count}",
            "text": chunk_text.strip(),
            "title": file_path.stem.replace("-", " ").replace("_", " ").title(),
            "source_path": str(file_path),
            "source_url": BASE_URL + str(
    file_path.relative_to(DOCS_FOLDER)
    .with_suffix("")
).replace("\\", "/").replace(
    "nrp-site/src/content/docs/Documentation/", ""
) + "/",
            "chunk_index": chunk_index
        }

        output_path = OUTPUT_FOLDER / f"chunk-{chunk_count}.json"

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(chunk, file, indent=2, ensure_ascii=False)

        chunk_count += 1

print(f"Created {chunk_count} chunks in {OUTPUT_FOLDER}")

if chunk_count < 100:
    print("Warning: fewer than 100 chunks were created.")
