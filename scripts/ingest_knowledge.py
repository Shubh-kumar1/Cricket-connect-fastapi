import asyncio
import json
from pathlib import Path

import faiss
import numpy as np
from fastapi import HTTPException

from app.config import get_settings
from app.services.chat import create_embedding, split_document


async def ingest_knowledge() -> int:
    documents_dir = Path("knowledge")
    documents = sorted(documents_dir.rglob("*.md"))
    if not documents:
        raise RuntimeError("No Markdown documents found in the knowledge directory.")

    chunks: list[dict[str, str]] = []
    for document in documents:
        content = document.read_text(encoding="utf-8")
        for position, chunk in enumerate(split_document(content)):
            chunks.append(
                {
                    "content": chunk,
                    "source": document.relative_to(documents_dir).as_posix(),
                    "chunk": str(position),
                }
            )
    embeddings: list[np.ndarray] = []
    for chunk in chunks:
        embeddings.append(await create_embedding(chunk["content"]))

    matrix = np.vstack(embeddings).astype(np.float32)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    index_path = Path(get_settings().chat_index_dir)
    index_path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path / "index.faiss"))
    (index_path / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(chunks)


def main() -> None:
    try:
        count = asyncio.run(ingest_knowledge())
    except HTTPException as exc:
        raise SystemExit(str(exc.detail)) from exc
    print(f"Indexed {count} chunks from verified knowledge documents.")


if __name__ == "__main__":
    main()
