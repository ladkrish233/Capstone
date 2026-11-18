import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from docx import (
    Document as DocxDocument,  # renamed so it never clashes with LangChain's Document
)
from pypdf import PdfReader


@dataclass
class Doc:
    id: str
    source: str
    kind: str
    title: str
    text: str


def clean(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_markdown(folder: str) -> list[Doc]:
    docs = []
    for path in sorted(Path(folder).glob("**/*.md")):
        text = clean(path.read_text(encoding="utf-8"))
        if not text:
            continue
        m = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        title = m.group(1).strip() if m else path.stem
        docs.append(
            Doc(id=path.stem, source=str(path), kind="markdown", title=title, text=text)
        )
    return docs


def load_text(folder: str) -> list[Doc]:
    docs = []
    for path in sorted(Path(folder).glob("**/*.txt")):
        text = clean(path.read_text(encoding="utf-8"))
        if not text:
            continue
        docs.append(
            Doc(
                id=path.stem,
                source=str(path),
                kind="markdown",
                title=path.stem,
                text=text,
            )
        )
    return docs


def load_pdfs(folder: str) -> list[Doc]:
    docs = []
    for path in sorted(Path(folder).glob("**/*.pdf")):
        pages_text = []
        for page in PdfReader(path).pages:
            pages_text.append(page.extract_text() or "")
        text = clean("\n\n".join(pages_text))
        if len(text.split()) < 50:
            print(f"skipped (almost no text): {path.name}")
            continue
        docs.append(
            Doc(id=path.stem, source=str(path), kind="pdf", title=path.stem, text=text)
        )
    return docs


def load_csv(folder: str, rows_per_doc: int = 15) -> list[Doc]:
    docs = []
    for path in sorted(Path(folder).glob("**/*.csv")):
        try:
            df = pd.read_csv(
                path,
                encoding="utf-8-sig",
                dtype=str,
                keep_default_na=False,
                on_bad_lines="skip",
                nrows=5000,
            )
        except pd.errors.EmptyDataError:
            print(f"skipped (empty): {path.name}")
            continue

        # tidy the table
        df.columns = [str(c).strip() for c in df.columns]
        df = df[df.apply(lambda row: any(v.strip() for v in row), axis=1)]

        # one line of text per row
        row_lines = []
        for row in df.to_dict("records"):
            parts = [f"{col}: {val.strip()}" for col, val in row.items() if val.strip()]
            if parts:
                row_lines.append("; ".join(parts))

        if not row_lines:
            print(f"skipped (no rows): {path.name}")
            continue

        header = f"File: {path.name}. Columns: {', '.join(df.columns)}"

        # one Doc per group of rows
        for start in range(0, len(row_lines), rows_per_doc):
            group = row_lines[start : start + rows_per_doc]
            text = clean(header + "\n" + "\n".join(group))
            docs.append(
                Doc(
                    id=f"{path.stem}-{start // rows_per_doc}",
                    source=str(path),
                    kind="csv",
                    title=f"{path.stem} (rows {start + 1}-{start + len(group)})",
                    text=text,
                )
            )
    return docs


def load_docx(folder: str) -> list[Doc]:
    docs = []
    for path in sorted(Path(folder).glob("**/*.docx")):
        if path.name.startswith("~$"):  # Word's temporary lock files
            continue
        try:
            d = DocxDocument(path)
        except Exception:
            print(f"skipped (cannot open): {path.name}")
            continue

        lines, title = [], None
        for p in d.paragraphs:
            t = p.text.strip()
            if not t:
                continue
            style = p.style.name if p.style is not None else ""
            if style.startswith("Heading"):
                title = title or t
                lines.append(f"# {t}")
            else:
                lines.append(t)

        for table in d.tables:  # tables are not inside d.paragraphs
            for row in table.rows:
                cells = []
                for c in row.cells:
                    v = c.text.strip()
                    if v and (
                        not cells or cells[-1] != v
                    ):  # skip empty and merged duplicates
                        cells.append(v)
                if cells:
                    lines.append(" | ".join(cells))

        text = clean("\n\n".join(lines))
        if len(text.split()) < 20:
            print(f"skipped (almost no text): {path.name}")
            continue
        docs.append(
            Doc(
                id=path.stem,
                source=str(path),
                kind="docx",
                title=title or path.stem,
                text=text,
            )
        )
    return docs


def load_html(folder: str) -> list[Doc]:
    docs = []
    files = [
        p
        for p in sorted(Path(folder).glob("**/*"))
        if p.suffix.lower() in {".html", ".htm"}
    ]
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw, "lxml")

        title = soup.title.get_text(strip=True) if soup.title else None
        if not title and soup.h1:
            title = soup.h1.get_text(strip=True)

        # remove everything that is not real page content, including hidden text
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "noscript",
                "svg",
                "form",
                "iframe",
            ]
        ):
            tag.decompose()
        for tag in soup.find_all(attrs={"hidden": True}):
            tag.decompose()
        for tag in soup.find_all(
            style=re.compile(
                r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE
            )
        ):
            tag.decompose()

        body = soup.body or soup
        text = clean(body.get_text("\n", strip=True))
        if len(text.split()) < 20:
            print(f"skipped (almost no text): {path.name}")
            continue
        docs.append(
            Doc(
                id=path.stem,
                source=str(path),
                kind="html",
                title=title or path.stem,
                text=text,
            )
        )
    return docs


def main():
    docs = (
        load_markdown("data/notes")
        + load_pdfs("data/pdfs")
        + load_csv("data/csv")
        + load_docx("data/docx")
        + load_html("data/html")
    )

    print(f"loaded {len(docs)} documents")
    for kind, n in Counter(d.kind for d in docs).items():
        print(f"  {kind}: {n}")

    words = [len(d.text.split()) for d in docs]
    if docs:
        print(f"shortest: {min(words)} words, longest: {max(words)} words")

    # clean check: nothing from front matter or comments should survive
    dirty = [d.source for d in docs if "<!--" in d.text or d.text.startswith("---")]
    print(f"dirty docs: {len(dirty)}", dirty[:3])

    # one sample per kind
    shown = set()
    for d in docs:
        if d.kind not in shown:
            shown.add(d.kind)
            print(f"\n[{d.kind}] {d.title} ({d.source})")
            print(d.text[:200])


if __name__ == "__main__":
    main()
