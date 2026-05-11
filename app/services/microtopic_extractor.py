from __future__ import annotations

import hashlib
import re

from app.domain.models import MicroTopic, TopicNode


class MicroTopicExtractor:
    MARKER_ALIASES = {
        "conceito": "Conceito",
        "definicao": "Definicao",
        "excecao": "Excecao",
        "regra": "Regra",
        "aplicacao": "Aplicacao",
        "observacao": "Observacao",
    }

    DIFFICULTY_WEIGHTS = {
        "excecao": 1.4,
        "observacao": 1.2,
        "conceito": 1.0,
    }

    def extract(self, topic: TopicNode) -> list[MicroTopic]:
        normalized = topic.content.strip()
        if not normalized:
            return []

        chunks = self._split_into_chunks(normalized)
        microtopics: list[MicroTopic] = []
        for index, chunk in enumerate(chunks):
            title, content = self._resolve_title_and_content(topic.title, chunk, index)
            content = content.strip()
            if not content:
                continue
            microtopics.append(
                MicroTopic(
                    id=self._build_id(topic.title, title, content, index),
                    title=title,
                    content=content,
                    source_topic_title=topic.title,
                    difficulty_weight=self._difficulty_weight(title),
                )
            )
        return microtopics

    def _split_into_chunks(self, content: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        chunks: list[str] = []
        for paragraph in paragraphs:
            bullet_lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            if bullet_lines and all(self._is_list_item(line) for line in bullet_lines):
                chunks.extend(self._normalize_list_item(line) for line in bullet_lines)
                continue
            chunks.append(paragraph)
        return chunks

    def _is_list_item(self, line: str) -> bool:
        return bool(re.match(r"^([-*]|\d+[.)])\s+", line))

    def _normalize_list_item(self, line: str) -> str:
        return re.sub(r"^([-*]|\d+[.)])\s+", "", line).strip()

    def _resolve_title_and_content(
        self,
        fallback_title: str,
        chunk: str,
        index: int,
    ) -> tuple[str, str]:
        first_line = chunk.splitlines()[0].strip()
        marker_match = re.match(
            r"^(conceito|definicao|excecao|regra|aplicacao|observacao)\s*:\s*(.*)$",
            first_line,
            flags=re.IGNORECASE,
        )
        if marker_match:
            marker_key = self._normalize_token(marker_match.group(1))
            title = self.MARKER_ALIASES[marker_key]
            remainder = marker_match.group(2).strip()
            tail_lines = chunk.splitlines()[1:]
            content_parts = [part for part in [remainder, *tail_lines] if part.strip()]
            return title, "\n".join(content_parts).strip()

        if "\n" not in chunk and len(chunk) <= 80:
            return first_line, chunk

        return f"{fallback_title} {index + 1}", chunk

    def _difficulty_weight(self, title: str) -> float:
        token = self._normalize_token(title)
        return self.DIFFICULTY_WEIGHTS.get(token, 1.0)

    def _build_id(self, source_topic_title: str, title: str, content: str, index: int) -> str:
        digest = hashlib.sha1(
            f"{source_topic_title}|{title}|{content}|{index}".encode("utf-8")
        ).hexdigest()[:12]
        return f"micro-{digest}"

    def _normalize_token(self, value: str) -> str:
        normalized = value.strip().lower()
        replacements = str.maketrans(
            {
                "á": "a",
                "à": "a",
                "â": "a",
                "ã": "a",
                "é": "e",
                "ê": "e",
                "í": "i",
                "ó": "o",
                "ô": "o",
                "õ": "o",
                "ú": "u",
                "ç": "c",
            }
        )
        return normalized.translate(replacements)
