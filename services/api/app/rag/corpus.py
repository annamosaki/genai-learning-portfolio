"""Load Anna's CV as a single plain-text context for Ask."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

def _cv_path() -> Path:
    """Resolve content/cv.ts for local repo layout and Lambda image (/var/task)."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[4] / "content" / "cv.ts",  # repo: services/api/app/rag → root
        here.parents[2] / "content" / "cv.ts",  # image: /var/task/app/rag → /var/task
        Path("/var/task/content/cv.ts"),
    )
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


CV_PATH = _cv_path()


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    text: str


def _str_field(src: str, key: str) -> str | None:
    m = re.search(rf'{key}:\s*"((?:\\.|[^"\\])*)"', src)
    return m.group(1).replace('\\"', '"') if m else None


def _str_list(src: str, key: str) -> list[str]:
    m = re.search(rf"{key}:\s*\[(.*?)\]", src, re.S)
    if not m:
        return []
    return [s.replace('\\"', '"') for s in re.findall(r'"((?:\\.|[^"\\])*)"', m.group(1))]


def _object_blocks(src: str, array_key: str) -> list[str]:
    m = re.search(rf"{array_key}:\s*\[", src)
    if not m:
        return []
    i = m.end()
    depth = 1
    blocks: list[str] = []
    obj_start: int | None = None
    while i < len(src) and depth > 0:
        ch = src[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        elif ch == "{" and depth == 1:
            obj_start = i
        elif ch == "}" and depth == 1 and obj_start is not None:
            blocks.append(src[obj_start : i + 1])
            obj_start = None
        i += 1
    return blocks


def build_chunks(raw: str) -> list[Chunk]:
    chunks: list[Chunk] = []

    name = _str_field(raw, "name") or "Anna Mosaki"
    title = _str_field(raw, "title") or ""
    seeking = _str_field(raw, "seeking") or ""
    location = _str_field(raw, "location") or ""
    email = _str_field(raw, "email") or ""
    phone = _str_field(raw, "phone") or ""
    summary = _str_field(raw, "summary") or ""

    links_block = re.search(r"links:\s*\{(.*?)\}", raw, re.S)
    links: dict[str, str] = {}
    if links_block:
        for k, v in re.findall(r'(\w+):\s*"((?:\\.|[^"\\])*)"', links_block.group(1)):
            links[k] = v

    profile_lines = [
        f"Name: {name}",
        f"Title: {title}",
        f"Location: {location}",
        f"Email: {email}",
        f"Phone: {phone}",
        f"Seeking: {seeking}",
        f"Summary: {summary}",
    ]
    if links:
        profile_lines.append("Links: " + ", ".join(f"{k}={v}" for k, v in links.items()))
    chunks.append(Chunk("profile", "Profile & contact", "\n".join(profile_lines)))

    lang_blocks = _object_blocks(raw, "languages")
    if lang_blocks:
        spoken = []
        for b in lang_blocks:
            label = _str_field(b, "label") or ""
            level = _str_field(b, "level") or ""
            if label:
                spoken.append(f"{label} ({level})" if level else label)
        chunks.append(Chunk("spoken-languages", "Spoken languages", "; ".join(spoken)))

    skills_m = re.search(r"skills:\s*\{(.*?)\n  \},", raw, re.S)
    if skills_m:
        skills_src = skills_m.group(1)
        parts = []
        for key in ("languages", "ml", "finance", "tools"):
            items = _str_list(skills_src, key)
            if items:
                parts.append(f"{key}: {', '.join(items)}")
        chunks.append(Chunk("skills", "Technical skills & stack", "\n".join(parts)))

    for i, block in enumerate(_object_blocks(raw, "experience")):
        company = _str_field(block, "company") or "Unknown"
        role = _str_field(block, "role") or ""
        loc = _str_field(block, "location") or ""
        start = _str_field(block, "start") or ""
        end = _str_field(block, "end") or ""
        bullets = _str_list(block, "bullets")
        text = (
            f"Company: {company}\nRole: {role}\nLocation: {loc}\n"
            f"Period: {start} – {end}\n"
            + "\n".join(f"- {b}" for b in bullets)
        )
        chunks.append(Chunk(f"experience-{i}", f"Experience: {company}", text))

    for i, block in enumerate(_object_blocks(raw, "education")):
        school = _str_field(block, "school") or ""
        degree = _str_field(block, "degree") or ""
        loc = _str_field(block, "location") or ""
        years = _str_field(block, "years") or ""
        notes = _str_list(block, "notes")
        text = f"School: {school}\nDegree: {degree}\nLocation: {loc}\nYears: {years}"
        if notes:
            text += "\n" + "\n".join(f"- {n}" for n in notes)
        chunks.append(Chunk(f"education-{i}", f"Education: {school}", text))

    for i, block in enumerate(_object_blocks(raw, "wins")):
        win_title = _str_field(block, "title") or ""
        org = _str_field(block, "org") or ""
        detail = _str_field(block, "detail") or ""
        chunks.append(Chunk(f"win-{i}", f"Award: {win_title}", f"{win_title} — {org}. {detail}"))

    prior = _str_list(raw, "priorProjects")
    if prior:
        chunks.append(
            Chunk("prior-projects", "Prior academic & hackathon projects", "\n".join(f"- {p}" for p in prior))
        )

    for i, block in enumerate(_object_blocks(raw, "activities")):
        act_title = _str_field(block, "title") or ""
        period = _str_field(block, "period") or ""
        detail = _str_field(block, "detail") or ""
        chunks.append(
            Chunk(f"activity-{i}", f"Activity: {act_title}", f"{act_title} ({period}). {detail}")
        )

    for i, block in enumerate(_object_blocks(raw, "projects")):
        p_title = _str_field(block, "title") or ""
        tagline = _str_field(block, "tagline") or ""
        status = _str_field(block, "status") or ""
        stack = _str_list(block, "stack")
        coming = _str_list(block, "comingSoon")
        text = f"Project: {p_title}\nTagline: {tagline}\nStatus: {status}"
        if stack:
            text += f"\nStack: {', '.join(stack)}"
        if coming:
            text += "\nComing soon:\n" + "\n".join(f"- {c}" for c in coming)
        chunks.append(Chunk(f"project-{i}", f"Planned project: {p_title}", text))

    return chunks


def get_chunks() -> tuple[Chunk, ...]:
    """Reload from disk each call so CV edits apply without restarting the API."""
    path = _cv_path()
    if not path.exists():
        return tuple()
    return tuple(build_chunks(path.read_text(encoding="utf-8")))


def full_cv_context() -> str:
    """Entire CV as one prompt context (no retrieval)."""
    parts = [f"## {c.title}\n{c.text}" for c in get_chunks()]
    return "\n\n".join(parts)


def corpus_char_count() -> int:
    return len(full_cv_context())
