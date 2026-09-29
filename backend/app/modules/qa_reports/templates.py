"""Small, non-executable text templates. Values are never parsed as template code."""

import re
from collections.abc import Mapping

REPORT_KEYS = {"report_title", "report_date", "author_name"}
ACTIVITY_KEYS = {
    "activity_code",
    "environment",
    "result",
    "coverage_links",
    "current_issue",
    "current_status",
}
TOKEN = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
KEY = re.compile(r"[a-z][a-z0-9_]{0,49}")
BLOCK = re.compile(r"\{\{\s*#activities\s*\}\}(.*?)\{\{\s*/activities\s*\}\}", re.DOTALL)
STANDALONE_BLOCK = re.compile(
    r"^[ \t]*(\{\{\s*(?:#|/)activities\s*\}\})[ \t]*(?:\r?\n|$)", re.MULTILINE
)
MAX_OUTPUT = 2_000_000


def normalize_body(body: str) -> str:
    # Pasted Markdown sometimes escapes underscores inside placeholder names.
    return TOKEN.sub(lambda match: match.group(0).replace(r"\_", "_"), body)


def activity_keys(body: str) -> list[str]:
    return list(
        dict.fromkeys(
            token
            for block in BLOCK.finditer(normalize_body(body))
            for match in TOKEN.finditer(block.group(1))
            if KEY.fullmatch(token := match.group(1).strip()) and token not in REPORT_KEYS
        )
    )


def custom_keys(body: str) -> list[str]:
    return list(
        dict.fromkeys(
            token
            for match in TOKEN.finditer(normalize_body(body))
            if KEY.fullmatch(token := match.group(1).strip())
            and token not in REPORT_KEYS | ACTIVITY_KEYS
        )
    )


def validate_body(body: str) -> str:
    body = normalize_body(body)
    if not body.strip() or len(body) > 20000:
        raise ValueError("Isi template wajib diisi, maksimal 20.000 karakter.")
    remainder = TOKEN.sub("", body)
    if "{{" in remainder or "}}" in remainder:
        raise ValueError("Placeholder belum ditutup. Gunakan {{nama_placeholder}}.")
    in_block = False
    blocks = 0
    for match in TOKEN.finditer(body):
        token = match.group(1).strip()
        if token == "#activities":
            if in_block:
                raise ValueError("Blok aktivitas tidak boleh bersarang.")
            in_block = True
            blocks += 1
        elif token == "/activities":
            if not in_block:
                raise ValueError("Penutup blok aktivitas tidak memiliki pembuka.")
            in_block = False
        elif not KEY.fullmatch(token):
            raise ValueError("Nama placeholder memakai huruf kecil, angka, dan underscore.")
        elif token in ACTIVITY_KEYS and not in_block:
            raise ValueError(f"{{{{{token}}}}} harus berada di dalam blok aktivitas.")
    if in_block:
        raise ValueError("Tutup blok aktivitas dengan {{/activities}}.")
    if blocks > 12 or len(custom_keys(body)) > 30:
        raise ValueError("Maksimal 12 blok aktivitas dan 30 placeholder tambahan.")
    return body


def render_body(body: str, report: Mapping[str, str], activities: list[dict[str, str]]) -> str:
    body = STANDALONE_BLOCK.sub(r"\1", validate_body(body))
    pieces: list[str] = []
    size = 0

    def append(value: str) -> None:
        nonlocal size
        size += len(value)
        if size > MAX_OUTPUT:
            raise ValueError("Hasil template terlalu panjang. Kurangi blok atau isian laporan.")
        pieces.append(value)

    def fill(source: str, values: Mapping[str, str]) -> str:
        return TOKEN.sub(lambda match: values.get(match.group(1).strip(), ""), source)

    cursor = 0
    for block in BLOCK.finditer(body):
        append(fill(body[cursor : block.start()], report))
        for item in activities:
            append(fill(block.group(1), {**report, **item}))
        cursor = block.end()
    append(fill(body[cursor:], report))
    return "".join(pieces).strip()
