from pathlib import Path

from app.services.markdown_loader import MarkdownContentSource


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_markdown_loader_parses_single_level_markdown(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(
        content_root / "single.md",
        "# Imunidades\nConteudo introdutorio.\nMais detalhes.\n",
    )

    loaded = MarkdownContentSource(content_root).load()

    assert len(loaded) == 1
    assert loaded[0].title == "Imunidades"
    assert len(loaded[0].topics) == 1
    assert loaded[0].topics[0].title == "Imunidades"
    assert loaded[0].topics[0].level == 1
    assert "Conteudo introdutorio." in loaded[0].topics[0].content


def test_markdown_loader_builds_nested_heading_hierarchy(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(
        content_root / "nested.md",
        (
            "# Navegacao\n"
            "Visao geral.\n"
            "## Regras gerais\n"
            "Texto das regras.\n"
            "### Excecoes\n"
            "Texto das excecoes.\n"
        ),
    )

    loaded = MarkdownContentSource(content_root).load()
    root_topic = loaded[0].topics[0]

    assert root_topic.title == "Navegacao"
    assert len(root_topic.children) == 1
    assert root_topic.children[0].title == "Regras gerais"
    assert root_topic.children[0].level == 2
    assert root_topic.children[0].children[0].title == "Excecoes"
    assert root_topic.children[0].children[0].level == 3


def test_markdown_loader_preserves_section_content(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(
        content_root / "content.md",
        (
            "# Balizamento\n"
            "Primeira linha.\n"
            "Segunda linha.\n"
            "## Criticos\n"
            "Alerta 1.\n"
            "Alerta 2.\n"
        ),
    )

    loaded = MarkdownContentSource(content_root).load()
    root_topic = loaded[0].topics[0]
    child_topic = root_topic.children[0]

    assert root_topic.content == "Primeira linha.\nSegunda linha."
    assert child_topic.content == "Alerta 1.\nAlerta 2."


def test_markdown_loader_loads_multiple_markdown_files(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(content_root / "a.md", "# A\nConteudo A.\n")
    write_markdown(content_root / "b.md", "# B\nConteudo B.\n")

    loaded = MarkdownContentSource(content_root).load()

    assert len(loaded) == 2
    assert {item.title for item in loaded} == {"A", "B"}


def test_markdown_loader_scans_recursive_folders(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(content_root / "folder1" / "one.md", "# Um\nConteudo.\n")
    write_markdown(content_root / "folder2" / "deep" / "two.md", "# Dois\nConteudo.\n")

    loaded = MarkdownContentSource(content_root).load()

    assert len(loaded) == 2
    assert {
        Path(item.source_path).name for item in loaded
    } == {"one.md", "two.md"}


def test_markdown_loader_preserves_empty_sections(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(
        content_root / "empty.md",
        "# Base\n## Vazio\n### Tambem vazio\n",
    )

    loaded = MarkdownContentSource(content_root).load()
    root_topic = loaded[0].topics[0]

    assert root_topic.children[0].content == ""
    assert root_topic.children[0].children[0].content == ""


def test_markdown_loader_tolerates_malformed_markdown(tmp_path):
    content_root = tmp_path / "content"
    write_markdown(
        content_root / "malformed.md",
        (
            "Texto solto antes do titulo.\n"
            "### Subtopico sem pai explicito\n"
            "Conteudo do subtopico.\n"
            "#### Heading fora do escopo vira texto\n"
        ),
    )

    loaded = MarkdownContentSource(content_root).load()

    assert len(loaded) == 1
    assert loaded[0].title == "malformed"
    assert len(loaded[0].topics) == 1
    assert loaded[0].topics[0].title == "Subtopico sem pai explicito"
    assert "Heading fora do escopo vira texto" in loaded[0].topics[0].content
