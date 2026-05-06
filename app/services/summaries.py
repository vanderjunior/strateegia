from __future__ import annotations

import re
from collections import Counter

from app.domain.models import Topic, TopicSummary


class SummaryGenerator:
    def generate(self, topic: Topic) -> TopicSummary:
        sentences = self._split_sentences(topic.content)
        ranked = self._rank_sentences(sentences)
        top_sentences = [sentence for sentence, _ in ranked[:2]] or sentences[:2]
        key_points = topic.key_points or [sentence for sentence, _ in ranked[:3]]
        trap_points = topic.trap_points or self._extract_traps(sentences)

        return TopicSummary(
            topic_id=topic.id,
            title=topic.title,
            structured_summary=" ".join(top_sentences).strip(),
            key_points=key_points[:3],
            trap_points=trap_points[:3],
        )

    def _split_sentences(self, content: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", content)
            if sentence.strip()
        ]

    def _rank_sentences(self, sentences: list[str]) -> list[tuple[str, int]]:
        frequencies = Counter(
            token.lower()
            for sentence in sentences
            for token in re.findall(r"[A-Za-zÀ-ÿ]+", sentence)
            if len(token) > 4
        )
        ranked = []
        for sentence in sentences:
            score = sum(
                frequencies[token.lower()]
                for token in re.findall(r"[A-Za-zÀ-ÿ]+", sentence)
                if len(token) > 4
            )
            ranked.append((sentence, score))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def _extract_traps(self, sentences: list[str]) -> list[str]:
        markers = ("exce", "salvo", "nao", "confundir")
        traps = [
            sentence
            for sentence in sentences
            if any(marker in sentence.lower() for marker in markers)
        ]
        return traps or ["A banca tende a explorar comparacoes, excecoes e termos absolutos."]
