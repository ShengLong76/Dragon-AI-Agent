#!/usr/bin/env python3
"""Rebrand user-visible framework naming to Dragon AI.

Desktop sources: only the *contents* of string literals ('...', "...", `...`
outside ${...}) and JSX text are rewritten. Python: only single-line string
literals (and f-string text) in PYTHON_TARGETS, the modules whose messages
reach the UI; docstrings and other triple-quoted strings are left alone. Identifiers, object keys, comments, imports and
lowercase storage keys are left untouched, so the code keeps compiling and
persisted state keeps its keys. Run it again after every upstream sync:

    python3 scripts/dragon/rebrand_strings.py            # rewrite in place
    python3 scripts/dragon/rebrand_strings.py --check    # exit 1 if anything is left
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "apps" / "desktop"
TARGETS = [DESKTOP / "src", DESKTOP / "electron"]
PYTHON_TARGETS = [
    ROOT / "agent" / "prompt_builder.py",
    ROOT / "agent" / "turn_failure_copy.py",
    ROOT / "agent" / "turn_recovery.py",
    ROOT / "hermes_cli" / "auth.py",
    ROOT / "tools" / "voice_live.py",
    ROOT / "tui_gateway" / "methods_prompt.py",
    ROOT / "tui_gateway" / "server.py",
    ROOT / "tui_gateway" / "user_messages.py",
]
SKIP_DIRS = {"node_modules", "dist", "fixtures"}
SKIP_FILES = {
    # Module specifiers and wire identifiers, not copy.
    "vite-env.d.ts",
}

# Applied in order; each pattern only ever sees literal text.
REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bHermes Agent \(by Nous Research\)"), "Dragon AI"),
    (re.compile(r"\bHermes Agent Desktop\b"), "Dragon AI"),
    (re.compile(r"\bHermes Desktop\b"), "Dragon AI"),
    (re.compile(r"\bHermes Agent\b"), "Dragon AI"),
    (re.compile(r"\bHermes Light\b"), "Dragon AI Light"),
    (re.compile(r"\bHermes Cloud\b"), "Dragon AI Cloud"),
    (re.compile(r"\bClassic Hermes\b"), "Classic Dragon"),
    (re.compile(r"\bHERMES AGENT\b"), "DRAGON AI"),
    (re.compile(r"\bHERMES\b"), "DRAGON AI"),
    (re.compile(r"\bHermes's\b"), "Dragon AI's"),
    (re.compile(r"\bHermes'(?=\s)"), "Dragon AI's"),
    (re.compile(r"\bHermes\b"), "Dragon AI"),
    (re.compile(r"~/\.hermes\b"), "~/.dragon-ai-claude"),
    (re.compile(r"%LOCALAPPDATA%\\\\hermes\b"), r"%LOCALAPPDATA%\\\\DragonAIClaude"),
    (re.compile(r"(?<![\w./-])hermes(?= (?:-p |--profile |model|auth|debug|curator|desktop|setup|update|gateway|doctor|config|login|tools|pm |skills|profile|cron|chat|serve|dashboard|plugins|mcp|status|logs|version|uninstall|claw|webhook|pairing|insights|sessions|memory|backup|import|acp|portal|whatsapp|honcho|kanban)\b)"), "dragon"),
    (re.compile(r"`hermes`"), "`dragon`"),
]

# Literals that are protocol/identity values, never shown as copy.
PROTECTED = re.compile(
    r"^(?:Hermes|HermesBundled|HermesLight|Hermes\.exe|hermes\.exe|NousResearch\.Hermes.*|Hermes-Setup.*|HERMES_[A-Z_]+)$"
)
# A literal that is only a ~/.hermes path names the backend's on-disk home (pm store, SSH remotes).
BARE_HOME_PATH = re.compile(r"^~/\.hermes(?:/[\w./-]*)?$")
# Filesystem paths and bundle names that point at real upstream artifacts.
PATHLIKE = re.compile(r"X-Hermes-|HERMES\.md|Hermes(?:\.app|\.exe|-Setup|\\|/)|[\\/]Hermes\b|\\\\hermes\b")
REGEX_KEYWORDS = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "yield", "await"}


def rebrand_text(text: str) -> str:
    if PROTECTED.match(text) or BARE_HOME_PATH.match(text) or PATHLIKE.search(text):
        return text
    for pattern, repl in REPLACEMENTS:
        text = pattern.sub(repl, text)
    return text


def transform_source(src: str, jsx: bool) -> str:
    out: list[str] = []
    i = 0
    n = len(src)
    # Stack of template-literal brace depths: when we re-enter code inside ${ },
    # we must know when the matching } returns us to the template.
    template_stack: list[int] = []
    brace_depth = 0
    prev_sig = ""  # last significant non-space char, to tell regex from division
    prev_word = ""

    def read_string(start: int, quote: str) -> int:
        j = start + 1
        while j < n:
            c = src[j]
            if c == "\\":
                j += 2
                continue
            if c == quote:
                return j
            if c == "\n" and quote != "`":
                return -1
            j += 1
        return -1

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            end = src.find("\n", i)
            end = n if end == -1 else end
            out.append(src[i:end])
            i = end
            continue
        if c == "/" and nxt == "*":
            end = src.find("*/", i + 2)
            end = n if end == -1 else end + 2
            out.append(src[i:end])
            i = end
            continue
        if c in "'\"":
            end = read_string(i, c)
            if end == -1:
                out.append(c)
                i += 1
                continue
            out.append(c + rebrand_text(src[i + 1 : end]) + c)
            i = end + 1
            prev_sig = c
            continue
        if c == "`" or (c == "}" and template_stack and template_stack[-1] == brace_depth):
            if c == "}":
                template_stack.pop()
                out.append("}")
            else:
                out.append("`")
            j = i + 1
            chunk: list[str] = []
            while j < n:
                d = src[j]
                if d == "\\":
                    chunk.append(src[j : j + 2])
                    j += 2
                    continue
                if d == "`":
                    out.append(rebrand_text("".join(chunk)) + "`")
                    j += 1
                    break
                if d == "$" and j + 1 < n and src[j + 1] == "{":
                    out.append(rebrand_text("".join(chunk)) + "${")
                    template_stack.append(brace_depth)
                    j += 2
                    break
                chunk.append(d)
                j += 1
            else:
                out.append("".join(chunk))
            i = j
            prev_sig = "`"
            continue
        regex_ctx = (prev_sig and prev_sig in "(,=:[!&|?{};+-*%<>~^") or (prev_word in REGEX_KEYWORDS and prev_sig == prev_word[-1:])
        if c == "/" and regex_ctx and nxt not in "/*":
            # Regex literal: copy verbatim.
            j = i + 1
            in_class = False
            while j < n:
                d = src[j]
                if d == "\\":
                    j += 2
                    continue
                if d == "[":
                    in_class = True
                elif d == "]":
                    in_class = False
                elif d == "/" and not in_class:
                    break
                elif d == "\n":
                    break
                j += 1
            out.append(src[i : j + 1])
            i = j + 1
            prev_sig = "/"
            continue
        if c == "{":
            brace_depth += 1
        elif c == "}":
            brace_depth -= 1
        if jsx and c == ">" and prev_sig != "=":
            # JSX text runs until the next tag or expression.
            m = re.match(r">([^<>{}`]*)(?=[<{])", src[i:])
            if m and re.search(r"[A-Za-z]", m.group(1)) and "\n\n" not in m.group(1):
                out.append(">" + rebrand_text(m.group(1)))
                i += len(m.group(0))
                prev_sig = ">"
                continue
        if c.isalpha() or c == "_" or c == "$":
            m = re.match(r"[^\W\d][\w$]*|\$[\w$]*", src[i:])
            word = m.group(0)
            out.append(word)
            i += len(word)
            prev_word = word
            prev_sig = word[-1]
            continue
        out.append(c)
        if not c.isspace():
            prev_sig = c
            prev_word = ""
        i += 1
    return "".join(out)


def transform_python(src: str) -> str:
    import io
    import tokenize

    line_starts = [0]
    for line in src.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))
    offset = lambda pos: line_starts[pos[0] - 1] + pos[1]  # noqa: E731
    edits: list[tuple[int, int, str]] = []
    middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == middle:
            new = rebrand_text(tok.string)
        elif tok.type == tokenize.STRING:
            m = re.match(r"([rRbBuUfF]*)('|\")(.*)\2$", tok.string, re.S)
            if not m or "b" in m.group(1).lower() or tok.string[len(m.group(1)):].startswith(("'''", '"""')):
                continue
            new = m.group(1) + m.group(2) + rebrand_text(m.group(3)) + m.group(2)
        else:
            continue
        if new != tok.string:
            edits.append((offset(tok.start), offset(tok.end), new))
    for start, end, new in reversed(edits):
        src = src[:start] + new + src[end:]
    return src


def iter_files() -> list[Path]:
    files: list[Path] = []
    for base in TARGETS:
        for path in base.rglob("*"):
            if path.suffix not in {".ts", ".tsx", ".mts"} or any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name in SKIP_FILES or ".test." in path.name or ".e2e." in path.name:
                continue
            files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report files that still need rebranding")
    args = parser.parse_args()
    changed: list[Path] = []
    for path in iter_files() + PYTHON_TARGETS:
        src = path.read_text(encoding="utf-8")
        new = transform_python(src) if path.suffix == ".py" else transform_source(src, jsx=path.suffix == ".tsx")
        if new != src:
            changed.append(path)
            if not args.check:
                path.write_text(new, encoding="utf-8")
    for path in changed:
        print(path.relative_to(ROOT))
    if args.check and changed:
        print(f"{len(changed)} file(s) still show framework naming", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
