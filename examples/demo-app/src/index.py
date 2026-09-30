"""Embedding pipeline."""

from openai import OpenAI

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"


def embed(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
