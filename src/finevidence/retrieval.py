import json
import math
import re
from collections import Counter
from pathlib import Path

from .models import Evidence

GENERIC_QUERY_TERMS = {"定义", "什么", "怎么", "如何", "请问", "告诉", "意思", "可以", "查询"}


def tokenize(text: str) -> list[str]:
    terms = re.findall(r"[a-z0-9_]+", text.lower())
    for span in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.extend(span)
        terms.extend(span[index : index + 2] for index in range(len(span) - 1))
    return terms


class BM25Index:
    def __init__(self, documents_path: Path):
        documents = json.loads(documents_path.read_text(encoding="utf-8"))
        self.chunks: list[Evidence] = []
        for document in documents:
            for index, paragraph in enumerate(document["text"].split("\n\n")):
                self.chunks.append(
                    Evidence(
                        id=f"{document['id']}:{index}",
                        title=document["title"],
                        text=paragraph,
                        source=document["source"],
                        company=document["company"],
                        year=document["year"],
                        score=0,
                    )
                )
        self.terms = [tokenize(f"{chunk.title} {chunk.text}") for chunk in self.chunks]
        self.counts = [Counter(terms) for terms in self.terms]
        self.df = Counter(term for terms in self.terms for term in set(terms))
        self.average_length = sum(map(len, self.terms)) / max(1, len(self.terms))

    def search(
        self, query: str, companies: list[str], years: list[int], limit: int = 3
    ) -> list[Evidence]:
        results: list[Evidence] = []
        query_terms = set(tokenize(query))
        for chunk, terms, counts in zip(self.chunks, self.terms, self.counts, strict=True):
            if companies:
                if chunk.company not in companies or (years and chunk.year not in years):
                    continue
            elif chunk.company is not None:
                continue
            if not any(
                len(term) >= 2 and term not in GENERIC_QUERY_TERMS and term in counts
                for term in query_terms
            ):
                continue
            score = 0.0
            for term in query_terms:
                frequency = counts[term]
                if frequency == 0:
                    continue
                idf = math.log(1 + (len(self.chunks) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denominator = frequency + 1.5 * (
                    1 - 0.75 + 0.75 * len(terms) / max(self.average_length, 1)
                )
                score += idf * frequency * 2.5 / denominator
            if score > 0:
                results.append(chunk.model_copy(update={"score": round(score, 6)}))
        results.sort(key=lambda chunk: (-chunk.score, chunk.id))
        return results[:limit]
