import os
import re
import shutil

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

FAISS_PATH = "faiss_index_shopeasy"
_embeddings = None
_vectorstore = None
_vectorstore_unavailable = False


def _faq_path() -> str:
    return "kb/shopeasy_faq.txt"

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        print("[RAG] Loading Embedding Model: all-MiniLM-L6-v2 ...")
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings

def initialize_kb(sample_text_path="kb/shopeasy_faq.txt"):
    """
    Creates the initial FAISS index if it doesn't exist.
    Caches it in memory to prevent reloading on every chat message. # Fix applied here.
    """
    global _vectorstore, _vectorstore_unavailable
    if _vectorstore is not None:
        return _vectorstore
    if _vectorstore_unavailable:
        return None

    if not os.path.exists(sample_text_path):
        os.makedirs(os.path.dirname(sample_text_path), exist_ok=True)
        with open(sample_text_path, "w") as f:
            f.write("Welcome to the support center FAQ.\n")
            f.write("1. For refunds, please wait 3-5 business days after your request.\n")
            f.write("2. For technical support, please try restarting your router first.\n")
            f.write("3. Order shipping typically takes 2 days for Prime members and 5 days for standard.\n")

    try:
        embeddings = get_embeddings()

        if os.path.exists(FAISS_PATH):
            print("[RAG] Loading existing FAISS index into memory...")
            _vectorstore = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
            return _vectorstore

        print("[RAG] Creating new FAISS index...")
        loader = TextLoader(sample_text_path)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
        splits = text_splitter.split_documents(docs)

        _vectorstore = FAISS.from_documents(splits, embeddings)
        _vectorstore.save_local(FAISS_PATH)
        return _vectorstore
    except Exception as exc:
        _vectorstore_unavailable = True
        print(f"[RAG] Vector search unavailable; using FAQ keyword search: {exc}")
        return None


def _keyword_context(query: str, k: int = 3) -> str:
    path = _faq_path()
    if not os.path.exists(path):
        return ""

    query_terms = {
        term for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2 and term not in {"the", "and", "for", "with", "what", "when", "does", "how", "can", "are", "after"}
    }
    if not query_terms:
        return ""

    with open(path, encoding="utf-8") as faq_file:
        lines = faq_file.readlines()

    ranked_lines = []
    for line in lines:
        text = line.strip()
        if not text or text.isupper():
            continue
        line_terms = set(re.findall(r"[a-z0-9]+", text.lower()))
        score = len(query_terms & line_terms)
        if score:
            ranked_lines.append((score, text))

    ranked_lines.sort(key=lambda item: item[0], reverse=True)
    return "\n".join(text for _, text in ranked_lines[:max(1, k)])

def retrieve_context(query: str, k=3):
    """
    Retrieve top-k contexts for Resolution Agent
    """
    vectorstore = initialize_kb()
    if vectorstore is None:
        return _keyword_context(query, k)

    docs = vectorstore.similarity_search(query, k=k)
    return "\n".join([d.page_content for d in docs])


def append_kb_text(text: str, category: str = "general"):
    """Append content to KB file and reindex FAISS."""
    if not text or not text.strip():
        return {"status": "skipped", "reason": "Empty KB text."}

    path = _faq_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n[{category.upper()}]\n")
        f.write(text.strip())
        f.write("\n")

    reindex_kb(path)
    return {"status": "ok", "message": "KB updated and reindexed."}


def reindex_kb(sample_text_path: str = None):
    """Force rebuild FAISS index from source text."""
    global _vectorstore, _vectorstore_unavailable
    if sample_text_path is None:
        sample_text_path = _faq_path()

    if os.path.exists(FAISS_PATH):
        # Clean old persisted index directory before rebuilding.
        shutil.rmtree(FAISS_PATH, ignore_errors=True)
    _vectorstore = None
    _vectorstore_unavailable = False
    return initialize_kb(sample_text_path=sample_text_path)

if __name__ == "__main__":
    initialize_kb()
