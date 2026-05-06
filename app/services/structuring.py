from __future__ import annotations

import re

from app.domain.models import Topic


class ContentStructurer:
    def __init__(self, chunk_size: int = 800):
        self.chunk_size = chunk_size

    def structure(self, raw_text: str) -> list[Topic]:
        normalized = self._normalize(raw_text)
        sections = self._extract_sections(normalized)
        if sections:
            return [
                self._build_topic(index=index, title=title, content=content)
                for index, (title, content) in enumerate(sections, start=1)
            ]
        return self._fallback_chunks(normalized)

    def _normalize(self, raw_text: str) -> str:
        raw_text = re.sub(r"\r\n?", "\n", raw_text)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _extract_sections(self, normalized: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        current_title: str | None = None
        current_lines: list[str] = []

        for line in normalized.splitlines():
            if self._is_heading(line):
                if current_title and current_lines:
                    sections.append((current_title, " ".join(current_lines).strip()))
                current_title = line.title()
                current_lines = []
                continue
            current_lines.append(line)

        if current_title and current_lines:
            sections.append((current_title, " ".join(current_lines).strip()))

        return [section for section in sections if section[1]]

    def _is_heading(self, line: str) -> bool:
        letters = [char for char in line if char.isalpha()]
        return bool(letters) and line == line.upper() and len(line) <= 80

    def _fallback_chunks(self, normalized: str) -> list[Topic]:
        chunks: list[str] = []
        cursor = 0
        while cursor < len(normalized):
            chunk = normalized[cursor : cursor + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)
            cursor += self.chunk_size

        return [
            self._build_topic(index=index, title=f"Topico {index}", content=chunk)
            for index, chunk in enumerate(chunks, start=1)
        ]

    def _build_topic(self, *, index: int, title: str, content: str) -> Topic:
        key_points = self._extract_key_points(content)
        trap_points = self._extract_trap_points(content)
        return Topic(
            id=f"topic-{index}",
            title=title.strip(),
            content=content.strip(),
            key_points=key_points,
            trap_points=trap_points,
            relevance_score=self._score_relevance(title, content),
            source_pages=[index],
        )

    def _extract_key_points(self, content: str) -> list[str]:
        sentences = self._split_sentences(content)
        return sentences[:3]

    def _extract_trap_points(self, content: str) -> list[str]:
        sentences = self._split_sentences(content)
        trap_markers = ("exceto", "exce", "nao confundir", "salvo", "pegadinha")
        traps = [
            sentence
            for sentence in sentences
            if any(marker in sentence.lower() for marker in trap_markers)
        ]
        if traps:
            return traps[:3]
        if sentences:
            return [f"Atencao para excecoes e comparacoes em {sentences[0]}"]
        return []

    def _score_relevance(self, title: str, content: str) -> float:
        lowered = f"{title} {content}".lower()
        keywords = [
            "importante",
            "relevante",
            "constituicao",
            "exce",
            "tribut",
            "fiscaliza",
            "competencia",
            "prova",
        ]
        score = 0.3 + sum(0.08 for keyword in keywords if keyword in lowered)
        return min(round(score, 2), 1.0)

    def _split_sentences(self, content: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", content)
        return [sentence.strip() for sentence in sentences if sentence.strip()]
