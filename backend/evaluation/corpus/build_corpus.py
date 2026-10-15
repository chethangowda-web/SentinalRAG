"""Turn the benchmark corpus (*.txt) into text-based PDFs, with no third-party dependencies.

    python backend/evaluation/corpus/build_corpus.py

The PDFs are committed next to the sources so the benchmark can be uploaded as-is; rerun this
only after editing a .txt file.
"""
import textwrap
from pathlib import Path

PAGE_WIDTH, PAGE_HEIGHT = 612, 792
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 56, 60, 60
FONT_SIZE, LEADING = 11, 15
WRAP_COLUMNS = 88
LINES_PER_PAGE = (PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM) // LEADING


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(text: str) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, WRAP_COLUMNS) or [""])
    return lines


def _paginate(lines: list[str]) -> list[list[str]]:
    return [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)] or [[]]


def _page_stream(lines: list[str]) -> bytes:
    out = [f"BT /F1 {FONT_SIZE} Tf {LEADING} TL {MARGIN_X} {PAGE_HEIGHT - MARGIN_TOP} Td"]
    for line in lines:
        out.append(f"({_escape(line)}) Tj T*")
    out.append("ET")
    return "\n".join(out).encode("latin-1", errors="replace")


def build_pdf(text: str) -> bytes:
    pages = _paginate(_wrap(text))

    # Object numbering: 1 catalog, 2 pages, 3 font, then (page, content) pairs.
    objects: list[bytes] = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for index, lines in enumerate(pages):
        page_obj = 4 + index * 2
        content_obj = page_obj + 1
        kids.append(f"{page_obj} 0 R")
        stream = _page_stream(lines)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(pdf)


def main() -> None:
    corpus_dir = Path(__file__).resolve().parent
    for source in sorted(corpus_dir.glob("*.txt")):
        target = source.with_suffix(".pdf")
        target.write_bytes(build_pdf(source.read_text(encoding="utf-8")))
        print(f"{source.name} -> {target.name} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
