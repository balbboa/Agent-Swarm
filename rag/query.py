import argparse
from typing import List

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


def query_index(
    persist_dir: str,
    question: str,
    model_name: str,
    device: str,
    k: int,
):
    embedding = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )
    vector_store = FAISS.load_local(
        persist_dir,
        embeddings=embedding,
        # For security, restrict to legacy format only if trusted environment
        allow_dangerous_deserialization=True,
    )
    docs = vector_store.similarity_search(question, k=k)
    return docs


def parse_args():
    parser = argparse.ArgumentParser(description="Query FAISS index")
    parser.add_argument(
        "--persist_dir",
        type=str,
        default="/home/arthur/challenge/data/index/faiss",
        help="Directory where FAISS index is stored",
    )
    parser.add_argument(
        "--question",
        type=str,
        required=True,
        help="Question to query the index",
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
    parser.add_argument("-k", type=int, default=5, help="Number of results")
    return parser.parse_args()


def main():
    args = parse_args()
    docs = query_index(
        persist_dir=args.persist_dir,
        question=args.question,
        model_name=args.model_name,
        device=args.device,
        k=args.k,
    )
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        print(f"[{i}] {source}")
        preview = doc.page_content
        if len(preview) > 500:
            preview = preview[:500] + "..."
        print(preview)
        print("-")


if __name__ == "__main__":
    main()



