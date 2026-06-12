from __future__ import annotations

import math
import sqlite3
from collections import Counter

from repolens import db
from repolens.embedding import HashEmbedding, cosine_similarity, tokenize
from repolens.models import CodeChunk, SearchResult


class HybridRetriever:
    def __init__(self, connection: sqlite3.Connection, embedding: HashEmbedding | None = None) -> None:
        self.connection = connection
        self.embedding = embedding or HashEmbedding()

    def search(self, query: str, repo_id: int | None = None, limit: int = 6) -> list[SearchResult]:
        chunks = db.fetch_chunks(self.connection, repo_id)
        if not chunks:
            return []

        query_tokens = tokenize(query)
        query_vector = self.embedding.embed(query)
        document_frequencies = build_document_frequencies(chunks)

        results: list[SearchResult] = []
        for chunk in chunks:
            keyword = keyword_score(query_tokens, chunk, document_frequencies, len(chunks))
            vector = max(0.0, cosine_similarity(query_vector, chunk.embedding))
            path = path_score(query_tokens, chunk)
            total = keyword * 0.50 + vector * 0.40 + path * 0.10
            if total > 0:
                results.append(SearchResult(chunk, total, keyword, vector, path))

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def build_document_frequencies(chunks: list[CodeChunk]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for chunk in chunks:
        frequencies.update(set(tokenize(chunk.content + " " + chunk.path + " " + (chunk.symbol or ""))))
    return frequencies


def keyword_score(
    query_tokens: list[str],
    chunk: CodeChunk,
    document_frequencies: Counter[str],
    document_count: int,
) -> float:
    if not query_tokens:
        return 0.0
    chunk_tokens = tokenize(chunk.content)
    metadata_tokens = tokenize(chunk.path + " " + (chunk.symbol or ""))
    counts = Counter(chunk_tokens)
    metadata_counts = Counter(metadata_tokens)
    score = 0.0
    for token in query_tokens:
        frequency = counts[token] + metadata_counts[token] * 2.0
        if frequency == 0:
            continue
        df = document_frequencies.get(token, 0)
        idf = math.log((document_count + 1) / (df + 0.5) + 1)
        score += idf * ((frequency * 2.2) / (frequency + 1.2))
    return min(score / max(len(set(query_tokens)), 1), 1.0)


def path_score(query_tokens: list[str], chunk: CodeChunk) -> float:
    haystack = f"{chunk.path} {chunk.symbol or ''}".lower()
    if not query_tokens:
        return 0.0
    unique_tokens = set(query_tokens)
    hits = sum(1 for token in unique_tokens if token in haystack)
    exact_symbol_bonus = 1.0 if chunk.symbol and chunk.symbol.lower() in unique_tokens else 0.0
    return min(1.5, hits / len(unique_tokens) + exact_symbol_bonus)
