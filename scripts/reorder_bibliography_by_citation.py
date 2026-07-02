#!/usr/bin/env python3
"""Reorder \\bibitem entries to match first \\cite appearance order in the .tex body."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def parse_bibitems(bib_text: str) -> dict[str, str]:
    items: dict[str, str] = {}
    pattern = re.compile(
        r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\\end\{thebibliography\})",
        re.DOTALL,
    )
    for m in pattern.finditer(bib_text):
        items[m.group(1)] = m.group(2).strip()
    return items


def first_cite_order(body: str) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"\\cite\{([^}]+)\}", body):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and key not in seen:
                seen.add(key)
                order.append(key)
    return order


def reorder_file(tex_path: Path) -> None:
    tex = tex_path.read_text(encoding="utf-8")
    m = re.search(r"\\begin\{thebibliography\}(\{[^}]*\})?", tex)
    if not m:
        raise SystemExit(f"No thebibliography in {tex_path}")

    bib_start = m.start()
    bib_end = tex.index("\\end{thebibliography}", bib_start) + len("\\end{thebibliography}")
    body = tex[:bib_start]
    bib_block = tex[bib_start:bib_end]
    tail = tex[bib_end:]

    items = parse_bibitems(bib_block)
    original_order = re.findall(r"\\bibitem\{([^}]+)\}", bib_block)
    cite_order = first_cite_order(body)
    uncited = [k for k in original_order if k not in set(cite_order)]
    new_order = cite_order + uncited

    missing = [k for k in cite_order if k not in items]
    if missing:
        raise SystemExit(f"Missing bibitems for cites: {missing}")

    width = m.group(1) or "{99}"
    lines = [f"\\begin{{thebibliography}}{width}", ""]
    for key in new_order:
        lines.append(f"\\bibitem{{{key}}} {items[key]}")
        lines.append("")
    lines.append("\\end{thebibliography}")

    tex_path.write_text(body + "\n".join(lines) + "\n" + tail, encoding="utf-8")
    print(
        f"Reordered {tex_path.name}: {len(cite_order)} cited + {len(uncited)} uncited "
        f"= {len(new_order)} entries"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tex_files",
        nargs="*",
        default=[
            str(_REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"),
            str(_REPO / "RL_MACPO_IEEE_English_with_images" / "conference_new_ready.tex"),
        ],
    )
    args = parser.parse_args()
    for path in args.tex_files:
        reorder_file(Path(path))


if __name__ == "__main__":
    main()
