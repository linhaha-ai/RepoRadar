"""README 结构化解析（基于 markdown-it-py）。

产出规则引擎所需的可枚举结构：
- 标题列表（level + 文本）
- 段落文本
- 代码块（语言标注）
- 链接（url 列表）
- 列表项数量
- 表格存在
"""

from __future__ import annotations

from dataclasses import dataclass, field

from markdown_it import MarkdownIt


@dataclass
class ReadmeDoc:
    headings: list[tuple[int, str]] = field(default_factory=list)   # (level, text)
    paragraphs: list[str] = field(default_factory=list)             # 纯文本段落
    code_blocks: list[str] = field(default_factory=list)            # 语言标注（空串=未标注）
    links: list[str] = field(default_factory=list)                  # http(s) 链接
    list_items: int = 0
    has_table: bool = False

    @property
    def full_text(self) -> str:
        return "\n".join(self.paragraphs)

    def heading_texts(self) -> list[str]:
        return [t.lower() for _, t in self.headings]


def _inline_text(tokens: list) -> str:
    parts: list[str] = []
    for t in tokens:
        if t.type == "text":
            parts.append(t.content)
        elif t.type == "code_inline":
            parts.append(t.content)
    return "".join(parts)


def parse_readme(text: str | None) -> ReadmeDoc:
    doc = ReadmeDoc()
    if not text or not text.strip():
        return doc

    md = MarkdownIt()
    tokens = md.parse(text)

    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            level = int(tok.tag[1])  # h1 -> 1
            # 下一个 token 是 inline
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                doc.headings.append((level, _inline_text(tokens[i + 1].children or [])))
        elif tok.type == "paragraph_open":
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                doc.paragraphs.append(_inline_text(tokens[i + 1].children or []))
        elif tok.type == "fence":
            doc.code_blocks.append((tok.info or "").strip())
        elif tok.type == "list_item_open":
            doc.list_items += 1
        elif tok.type == "table_open":
            doc.has_table = True
        elif tok.type == "inline":
            for child in tok.children or []:
                if child.type == "link_open":
                    href = child.attrs.get("href", "") if child.attrs else ""
                    if href.startswith(("http://", "https://")):
                        doc.links.append(href)

    return doc
