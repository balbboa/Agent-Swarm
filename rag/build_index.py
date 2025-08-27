import argparse
import os
from pathlib import Path
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


def collect_text_files(source_dir: str) -> List[Path]:
    base = Path(source_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Source dir not found or not a directory: {source_dir}")
    files: List[Path] = []
    for path in base.rglob("*.txt"):
        # Skip hidden and zero-length placeholders
        if path.name.startswith("."):
            continue
        files.append(path)
    return sorted(files)


def load_documents(file_paths: List[Path]) -> List[Document]:
    documents: List[Document] = []
    for file_path in file_paths:
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            text = file_path.read_text(encoding="latin-1")
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "relative_path": str(file_path),
        }
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def split_documents(documents: List[Document], chunk_size: int, chunk_overlap: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def build_faiss_index(
    source_dir: str,
    persist_dir: str,
    model_name: str,
    device: str,
    chunk_size: int,
    chunk_overlap: int,
):
    files = collect_text_files(source_dir)
    if not files:
        raise RuntimeError(f"No .txt files found under: {source_dir}")

    documents = load_documents(files)
    chunks = split_documents(documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    embedding = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    vector_store = FAISS.from_documents(documents=chunks, embedding=embedding)

    os.makedirs(persist_dir, exist_ok=True)
    vector_store.save_local(persist_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS index from knowledge base")
    parser.add_argument(
        "--source_dir",
        type=str,
        default="/home/arthur/challenge/data/knowledge",
        help="Directory containing .txt knowledge files",
    )
    parser.add_argument(
        "--persist_dir",
        type=str,
        default="/home/arthur/challenge/data/index/faiss",
        help="Directory to persist FAISS index",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="HuggingFace sentence-transformers model name",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for embeddings model: 'cpu' or 'cuda'",
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=1000,
        help="Chunk size for splitting documents",
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=150,
        help="Chunk overlap for splitting documents",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    build_faiss_index(
        source_dir=args.source_dir,
        persist_dir=args.persist_dir,
        model_name=args.model_name,
        device=args.device,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print(f"FAISS index built and saved to: {args.persist_dir}")


if __name__ == "__main__":
    main()



