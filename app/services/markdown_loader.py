from __future__ import annotations

import re
from pathlib import Path

from app.domain.models import StudyContent, TopicNode


class MarkdownContentSource:
    def __init__(self, root_path: Path | str | None = None):
        self.root_path = Path(root_path) if root_path else self.default_root_path()

    @staticmethod
    def default_root_path() -> Path:
        return Path(__file__).resolve().parents[1] / "repositories" / "content"

    def load(self) -> list[StudyContent]:
        if not self.root_path.exists():
            return []

        contents: list[StudyContent] = []
        for path in sorted(self.root_path.rglob("*.md")):
            contents.append(self._load_file(path))
        return contents

    def _load_file(self, path: Path) -> StudyContent:
        raw = path.read_text(encoding="utf-8")
        topics = self._parse_topics(raw, fallback_title=path.stem)
        document_title = (
            topics[0].title
            if topics and topics[0].level == 1
            else path.stem
        )
        return StudyContent(
            source_path=str(path),
            title=document_title,
            topics=topics,
        )

    def _parse_topics(self, raw_markdown: str, *, fallback_title: str) -> list[TopicNode]:
        heading_pattern = re.compile(r"^(#{1,3})\s+(.*\S)\s*$")
        roots: list[TopicNode] = []
        stack: list[TopicNode] = []
        content_lines: dict[int, list[str]] = {}
        preamble: list[str] = []

        for raw_line in raw_markdown.splitlines():
            line = raw_line.rstrip()
            heading_match = heading_pattern.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                node = TopicNode(
                    title=heading_match.group(2).strip(),
                    level=level,
                    content="",
                    children=[],
                )
                content_lines[id(node)] = []

                while stack and stack[-1].level >= level:
                    stack.pop()

                if stack:
                    stack[-1].children.append(node)
                else:
                    roots.append(node)
                    if preamble:
                        content_lines[id(node)].extend(preamble)
                        preamble = []

                stack.append(node)
                continue

            if stack:
                content_lines[id(stack[-1])].append(line)
            else:
                preamble.append(line)

        if not roots:
            return [
                TopicNode(
                    title=fallback_title,
                    level=1,
                    content=self._normalize_content(preamble),
                    children=[],
                )
            ]

        for node in roots:
            self._apply_content(node, content_lines)
        return roots

    def _apply_content(self, node: TopicNode, content_lines: dict[int, list[str]]) -> None:
        node.content = self._normalize_content(content_lines.get(id(node), []))
        for child in node.children:
            self._apply_content(child, content_lines)

    def _normalize_content(self, lines: list[str]) -> str:
        joined = "\n".join(lines)
        return joined.strip()
