#!/usr/bin/env python3
"""Check every chatbot folder and say, in plain English, what to fix.

    python _pages/scripts/validate.py           # check everything
    python _pages/scripts/validate.py my-bot    # check one folder
    python _pages/scripts/validate.py --strict  # treat warnings as failures

Exit code 0 means the pull request will pass CI.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    HANDLE_RE,
    KINDS,
    SLUG_RE,
    Bot,
    Issue,
    bold,
    dim,
    green,
    load_bots,
    red,
    yellow,
)

MAX_SCREENSHOT_BYTES = 3 * 1024 * 1024
SKIP_SCAN_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".ico"}
IMAGE_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")

# Deliberately narrow so it never cries wolf: real tokens and private keys only.
SECRET_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), "an API token starting with 'sk-'"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "a GitHub personal access token"),
]
ROTATE_HINT = (
    "Delete it, then rotate the token at https://nrp.ai/llmtoken. A token pushed to a "
    "public repo is leaked even if you remove it in the next commit."
)


class Checker:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.where = bot.slug
        self.issues: list[Issue] = []

    def error(self, message: str, fix: str = "") -> None:
        self.issues.append(Issue("error", self.where, message, fix))

    def warn(self, message: str, fix: str = "") -> None:
        self.issues.append(Issue("warning", self.where, message, fix))

    def check_slug(self) -> None:
        if not SLUG_RE.match(self.bot.slug):
            self.error(
                f"the folder name '{self.bot.slug}' isn't a valid slug",
                "Lowercase letters, numbers and single dashes only: 'mihir-chatbot'.",
            )

    def check_required(self) -> None:
        data = self.bot.data
        for field_name, kind in [
            ("name", str),
            ("tagline", str),
            ("kind", str),
            ("year", int),
        ]:
            value = data.get(field_name)
            if value is None:
                self.error(
                    f"'{field_name}' is missing from bot.yaml",
                    "Copy the shape from _pages/template/bot.yaml.",
                )
            elif not isinstance(value, kind) or (kind is str and not str(value).strip()):
                self.error(
                    f"'{field_name}' should be {'a number' if kind is int else 'text'}, "
                    f"got {value!r}"
                )

        name = str(data.get("name", ""))
        if len(name) > 60:
            self.error(f"'name' is {len(name)} characters, keep it under 60.")

        tagline = str(data.get("tagline", "")).strip()
        if tagline:
            if len(tagline) > 120:
                self.warn(
                    f"'tagline' is {len(tagline)} characters, keep it under 120.",
                    "It has to fit on a card and in a link preview.",
                )
            if tagline.lower() == name.lower():
                self.warn(
                    "'tagline' just repeats the bot's name",
                    "Say what it DOES: 'Answers NRP questions with citations from the docs.'",
                )
            elif len(tagline.split()) < 4:
                self.warn("'tagline' is very short, one full sentence reads better.")

        kind = data.get("kind")
        if isinstance(kind, str) and kind not in KINDS:
            self.error(f"'kind' must be one of {list(KINDS)}, got '{kind}'.")

        year = data.get("year")
        if isinstance(year, int) and not (2020 <= year <= 2100):
            self.error(f"'year' looks wrong: {year}. Use the cohort year, e.g. 2026.")

    def check_authors(self) -> None:
        authors = self.bot.data.get("authors")
        if not isinstance(authors, list) or not authors:
            self.error(
                "'authors' is missing or empty",
                "List everyone who built this bot, this is what creates your own page.",
            )
            return
        if len(authors) > 8:
            self.error(f"'authors' has {len(authors)} people, 8 is the maximum.")

        seen: set[str] = set()
        for i, author in enumerate(authors, start=1):
            at = f"authors[{i}]"
            if not isinstance(author, dict):
                self.error(f"{at} should be a block with name/github/role, got {author!r}")
                continue
            for field_name in ("name", "github", "role"):
                if not str(author.get(field_name, "")).strip():
                    self.error(f"{at} is missing '{field_name}'")

            handle = str(author.get("github", "")).strip().lstrip("@")
            if handle:
                if not HANDLE_RE.match(handle):
                    self.error(
                        f"{at}: '{handle}' isn't a valid GitHub handle",
                        "Just the handle, no '@', no URL.",
                    )
                if handle.lower() in seen:
                    self.error(f"{at}: '{handle}' is listed twice.")
                seen.add(handle.lower())

            role = str(author.get("role", "")).strip()
            if role and len(role) < 8:
                self.warn(
                    f"{at}: role '{role}' is vague",
                    "Name what you owned: 'retrieval + eval harness'.",
                )
            if len(role) > 120:
                self.warn(f"{at}: 'role' is over 120 characters, tighten it.")

            learned = str(author.get("learned", "")).strip()
            if not learned:
                self.warn(
                    f"{at}: no 'learned' note",
                    "Three honest sentences here is the best thing on your page.",
                )
            elif len(learned) > 700:
                self.error(f"{at}: 'learned' is very long, keep it under ~700 characters.")

    def check_links(self) -> None:
        links = self.bot.data.get("links")
        if links is None:
            return
        if not isinstance(links, dict):
            self.error(
                "'links' should be a block of name: url pairs, see ENTRY-FORMAT.md.",
            )
            return

        for field_name in ("repo_url", "demo_video", "slides"):
            url = links.get(field_name)
            if url and not str(url).startswith("https://"):
                self.error(f"'links.{field_name}' should start with https://, got '{url}'")

        if not links.get("repo_url"):
            self.warn(
                "no links.repo_url",
                "Optional, your code is in src/ either way. Add it if your bot also "
                "lives in its own public repo.",
            )

    def check_content(self) -> None:
        tech = self.bot.data.get("tech")
        if not isinstance(tech, list) or not tech:
            self.error("'tech' is missing", "List 3-8 things: Streamlit, ChromaDB, Kubernetes...")
        elif len(tech) > 12:
            self.error(f"'tech' has {len(tech)} entries, 12 is the maximum.")

        highlights = self.bot.data.get("highlights")
        if highlights is None:
            self.error(
                "'highlights' is missing",
                "2-5 bullets on what makes YOUR bot yours. Decisions, not features.",
            )
        elif isinstance(highlights, list):
            if not highlights:
                self.error(
                    "'highlights' is empty",
                    "2-5 bullets on what makes YOUR bot yours. Decisions, not features.",
                )
            else:
                if len(highlights) > 6:
                    self.error(f"'highlights' has {len(highlights)} bullets, 6 is the maximum.")
                for i, h in enumerate(highlights, start=1):
                    if len(str(h)) > 240:
                        self.error(f"highlights[{i}] is over 240 characters, split or trim it.")
        else:
            # A single block of prose is fine too — don't block a student for not
            # reaching for markdown bullets.
            if not str(highlights).strip():
                self.error(
                    "'highlights' is empty",
                    "2-5 bullets on what makes YOUR bot yours. Decisions, not features.",
                )

        readme = self.bot.path / "README.md"
        if not readme.exists():
            self.warn(
                "there's no README.md in this folder",
                "It becomes the body of your page. Start from _pages/template/README.md.",
            )
        elif len(self.bot.readme.strip()) < 400:
            self.warn(
                "README.md is very short",
                "The 'what I tried' section is what makes a page worth reading.",
            )
        elif "Delete these comments" in self.bot.readme:
            self.warn("README.md still contains the template's instructions, delete them.")

    def check_eval(self) -> None:
        ev = self.bot.data.get("eval")
        if ev is None:
            return
        if not isinstance(ev, dict):
            self.error("'eval' should be a block of numbers, see _pages/template/bot.yaml.")
            return
        total = ev.get("total")
        if not isinstance(total, int) or total <= 0:
            self.error("'eval.total' must be a positive number (how many questions).")
            return
        for field_name in ("retrieval_hit", "answer_ok"):
            value = ev.get(field_name)
            if value is None:
                continue
            if not isinstance(value, int) or value < 0:
                self.error(f"'eval.{field_name}' must be a number 0 or greater.")
            elif value > total:
                self.error(
                    f"'eval.{field_name}' is {value} but 'eval.total' is {total}",
                    "You can't score higher than the number of questions.",
                )

    def check_screenshot(self) -> None:
        name = self.bot.data.get("screenshot")
        if not name:
            self.warn(
                "no screenshot",
                "A picture of it answering a real question is the first thing anyone "
                "sees. Add one if you still can.",
            )
            return
        shot = self.bot.path / str(name)
        if not shot.exists():
            self.error(
                f"screenshot '{name}' isn't in this folder",
                "Add the image, or fix the filename in bot.yaml.",
            )
            return
        if shot.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            self.error(f"screenshot '{name}' must be a .png or .jpg file.")
            return
        head = shot.read_bytes()[:8]
        if not any(head.startswith(magic) for magic in IMAGE_MAGIC):
            self.error(
                f"screenshot '{name}' isn't a real PNG or JPEG",
                "Re-export it. (Renaming a .webp to .png doesn't convert it.)",
            )
        size = shot.stat().st_size
        if size > MAX_SCREENSHOT_BYTES:
            self.error(
                f"screenshot '{name}' is {size / 1024 / 1024:.1f} MB, the limit is 3 MB",
                "Resize it to about 1600px wide."
            )

    def check_code(self) -> None:
        """src/ is the code you wrote; k8s/ is what you applied to the cluster."""
        src = self.bot.path / "src"
        if not src.is_dir():
            self.error(
                "there's no src/ folder",
                "Put your chatbot's source code in src/, that's the evidence you built it.",
            )
        elif not self.bot.src_files:
            self.error("src/ is empty", "Copy your chatbot's code into it.")

        k8s = self.bot.path / "k8s"
        if not k8s.is_dir():
            self.error(
                "there's no k8s/ folder",
                "Put the Kubernetes manifests you applied in k8s/, deployment.yaml, "
                "service.yaml, ingress.yaml, pvc.yaml. Your page draws them as a diagram.",
            )
            return
        if not self.bot.k8s_files:
            self.error(
                "k8s/ has no .yaml files",
                "Copy in the manifests you ran `kubectl apply -f` on.",
            )
            return

        kinds = self.bot.kinds
        if not kinds:
            self.warn(
                "none of the files in k8s/ look like Kubernetes manifests",
                "Each should have an 'apiVersion' and a 'kind', check you copied the "
                "right files.",
            )
            return
        if "Deployment" not in kinds and "Pod" not in kinds and "StatefulSet" not in kinds:
            self.warn(
                f"k8s/ has no Deployment (found: {', '.join(kinds)})",
                "The Deployment is the manifest that actually runs your bot, include it.",
            )
        for kind in ("Service", "Ingress"):
            if kind not in kinds:
                self.warn(
                    f"k8s/ has no {kind}",
                    "Include it if you had one, the page shows the whole chain from the "
                    "internet to your pod.",
                )
        if "Secret" in kinds:
            self.error(
                "k8s/ contains a Secret manifest",
                "Never commit a Secret. Delete the file, the token was created on the "
                "cluster with `kubectl create secret`, and it does not belong in git. "
                + ROTATE_HINT,
            )

    def check_secrets(self) -> None:
        """Scan every text file in the folder, src/ and k8s/ are where tokens hide.
        Paths listed in the entry's `ignore_paths` are skipped: vendored docs repos
        legitimately contain example keys, and scanning them only cries wolf."""
        for path in sorted(self.bot.path.rglob("*")):
            if not path.is_file() or path.suffix.lower() in SKIP_SCAN_SUFFIXES:
                continue
            if path.stat().st_size > 2_000_000:
                continue
            rel = path.relative_to(self.bot.path).as_posix()
            if self.bot._ignored(rel):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern, description in SECRET_PATTERNS:
                if pattern.search(text):
                    self.error(f"{rel} contains what looks like {description}", ROTATE_HINT)
                    break
        env = self.bot.path / ".env"
        if env.exists():
            self.error(
                "there's a .env file in this folder",
                "That's where tokens live. Delete it, it must never be committed. "
                + ROTATE_HINT,
            )

    def run(self) -> list[Issue]:
        self.check_slug()
        self.check_required()
        self.check_authors()
        self.check_links()
        self.check_content()
        self.check_eval()
        self.check_screenshot()
        self.check_code()
        self.check_secrets()
        return self.issues


def check_across_bots(bots: list[Bot]) -> list[Issue]:
    issues: list[Issue] = []
    names: dict[str, str] = {}
    for bot in bots:
        key = bot.name.strip().lower()
        if key in names:
            issues.append(
                Issue(
                    "warning",
                    bot.slug,
                    f"'{bot.name}' is also the name of {names[key]}",
                    "Two bots with the same name is confusing in the gallery.",
                )
            )
        names[key] = bot.slug
    return issues


def report(issues: list[Issue], strict: bool, checked: int) -> int:
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    for issue in errors + warnings:
        tag = red("ERROR  ") if issue.level == "error" else yellow("WARN   ")
        print(f"{tag} {bold(issue.where)}: {issue.message}")
        if issue.fix:
            print(f"        {dim('-> ' + issue.fix)}")

    print()
    word = "entry" if checked == 1 else "entries"
    if not errors and not warnings:
        print(green(f"All good, {checked} {word} checked, nothing to fix."))
        return 0
    summary = f"{checked} {word} checked: {len(errors)} error(s), {len(warnings)} warning(s)."
    if errors:
        print(red(summary))
        print("Fix the errors above, then run this again.")
        return 1
    if strict:
        print(yellow(summary) + "  (--strict: warnings count as failures)")
        return 1
    print(yellow(summary))
    print("Warnings won't block your pull request, but they're worth fixing.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate showcase entries.")
    parser.add_argument("slug", nargs="?", help="check only this entry (folder name)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    loaded = load_bots()
    bots = loaded.bots

    if args.slug:
        wanted = args.slug.strip("/")
        bots = [b for b in bots if b.slug == wanted]
        if not bots:
            print(red(f"No chatbot folder called '{wanted}'."))
            print(dim("Available: " + (", ".join(b.slug for b in loaded.bots) or "(none yet)")))
            return 2

    issues = list(loaded.issues)
    for bot in bots:
        issues.extend(Checker(bot).run())
    if not args.slug:
        issues.extend(check_across_bots(bots))

    if not bots and not issues:
        print(yellow("No chatbot folders yet, nothing to check."))
        print(dim("Add one: cp -r _pages/template <your-bot-name>"))
        return 0

    return report(issues, args.strict, len(bots))


if __name__ == "__main__":
    raise SystemExit(main())
