import os
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

load_dotenv()


def _has_env(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value)


def _get_ollama_llm(temperature: float) -> Any:
    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        temperature=temperature,
    )


def get_llm(task: str = "general", temperature: float = 0.0, prefer_local: bool = False) -> Any:
    """
    Return an LLM instance selected by task and provider availability.

    Task routing policy:
    - routing/triage/resolution: Groq primary
    - critic: Gemini primary
    - escalation/local_sensitive: Ollama primary

    Fallback order is always safe and deterministic.
    """
    task = (task or "general").strip().lower()

    if prefer_local or task in {"escalation", "local_sensitive", "offline"}:
        return _get_ollama_llm(temperature)

    if task == "critic":
        if _has_env("GEMINI_API_KEY"):
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=temperature,
            )
        if _has_env("GROQ_API_KEY"):
            return ChatGroq(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
            )
        return _get_ollama_llm(temperature)

    if task == "voice":
        if _has_env("GROQ_API_KEY"):
            return ChatGroq(
                model=os.getenv("VOICE_GROQ_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
            )
        return _get_ollama_llm(temperature)

    if task == "email":
        if _has_env("GROQ_API_KEY"):
            return ChatGroq(
                model=os.getenv("EMAIL_GROQ_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
            )
        return _get_ollama_llm(temperature)

    if _has_env("GROQ_API_KEY"):
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=temperature,
        )

    if _has_env("GEMINI_API_KEY"):
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=temperature,
        )

    return _get_ollama_llm(temperature)
