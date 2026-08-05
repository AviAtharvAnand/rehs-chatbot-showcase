"""Shared helpers: find bot folders, load bot.yaml.

Used by validate.py and build_site.py. Nothing here touches the network.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Repo root. Each student's chatbot is a folder here containing a bot.yaml.
ROOT = Path(__file__).resolve().parent.parent.parent
PAGES_DIR = ROOT / "_pages"
SITE_DIR = ROOT / "site"
TEMPLATES_DIR = PAGES_DIR / "templates"
STATIC_DIR = PAGES_DIR / "static"

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

#: Root folders that are repo machinery, never chatbot entries. Anything starting
#: with "." or "_" is skipped too, so _pages/ needs no special case.
SKIP_DIRS = {"site", "node_modules"}

KINDS = ("solo", "pair", "team")


@dataclass
class Bot:
    """One chatbot folder at the repo root. `slug` is always the folder name."""

    slug: str
    path: Path
    data: dict
    readme: str = ""

    @property
    def name(self) -> str:
        return str(self.data.get("name", self.slug))

    @property
    def tagline(self) -> str:
        return str(self.data.get("tagline", ""))

    @property
    def kind(self) -> str:
        return str(self.data.get("kind", "solo"))

    @property
    def year(self) -> int | None:
        year = self.data.get("year")
        return int(year) if isinstance(year, int) else None

    @property
    def is_example(self) -> bool:
        """The reference entry, shown, badged, and left out of the cohort stats."""
        return bool(self.data.get("example", False))

    @property
    def authors(self) -> list[dict]:
        return [a for a in (self.data.get("authors") or []) if isinstance(a, dict)]

    @property
    def links(self) -> dict:
        return self.data.get("links") or {}

    @property
    def repo_url(self) -> str | None:
        url = self.links.get("repo_url")
        return str(url) if url else None

    @property
    def tech(self) -> list[str]:
        return [str(t) for t in (self.data.get("tech") or [])]

    @property
    def highlights(self) -> list[str]:
        return [str(h) for h in (self.data.get("highlights") or [])]

    @property
    def eval(self) -> dict | None:
        ev = self.data.get("eval")
        return ev if isinstance(ev, dict) else None

    # -- the folder's own contents -------------------------------------------

    @property
    def k8s_files(self) -> list[Path]:
        """The Kubernetes manifests the student actually applied."""
        k8s = self.path / "k8s"
        if not k8s.is_dir():
            return []
        return sorted(p for p in k8s.rglob("*") if p.suffix in (".yaml", ".yml"))

    @property
    def src_files(self) -> list[Path]:
        """Their source code, for the file list on the page."""
        src = self.path / "src"
        if not src.is_dir():
            return []
        return sorted(
            p
            for p in src.rglob("*")
            if p.is_file() and not p.name.startswith(".") and "__pycache__" not in p.parts
        )

    @property
    def resources(self) -> list[dict]:
        """Parse k8s/ into {kind, name, file, ...}, the page renders this, so what it
        shows is what they really deployed. Unparseable files are skipped, not fatal."""
        found: list[dict] = []
        for path in self.k8s_files:
            try:
                docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
            except yaml.YAMLError:
                continue
            for doc in docs:
                if not isinstance(doc, dict) or not doc.get("kind"):
                    continue
                meta = doc.get("metadata") or {}
                spec = doc.get("spec") or {}
                item = {
                    "kind": str(doc["kind"]),
                    "name": str(meta.get("name", "")) if isinstance(meta, dict) else "",
                    "namespace": str(meta.get("namespace", "")) if isinstance(meta, dict) else "",
                    "file": path.name,
                }
                if isinstance(spec, dict):
                    if item["kind"] == "Deployment" and isinstance(spec.get("replicas"), int):
                        item["replicas"] = spec["replicas"]
                    if item["kind"] == "PersistentVolumeClaim":
                        req = ((spec.get("resources") or {}).get("requests") or {})
                        if isinstance(req, dict) and req.get("storage"):
                            item["storage"] = str(req["storage"])
                    if item["kind"] == "Ingress":
                        rules = spec.get("rules") or []
                        if rules and isinstance(rules[0], dict) and rules[0].get("host"):
                            item["host"] = str(rules[0]["host"])
                found.append(item)
        # Show the chain the way traffic actually flows, not alphabetically by filename.
        order = {
            "Ingress": 0,
            "Service": 1,
            "Deployment": 2,
            "StatefulSet": 2,
            "Pod": 2,
            "Job": 3,
            "CronJob": 3,
            "ConfigMap": 4,
            "PersistentVolumeClaim": 5,
        }
        return sorted(found, key=lambda i: (order.get(i["kind"], 6), i["name"]))

    @property
    def namespace(self) -> str | None:
        for item in self.resources:
            if item.get("namespace"):
                return item["namespace"]
        return None

    @property
    def kinds(self) -> list[str]:
        seen: list[str] = []
        for item in self.resources:
            if item["kind"] not in seen:
                seen.append(item["kind"])
        return seen

    @property
    def screenshot(self) -> Path | None:
        name = self.data.get("screenshot")
        if not name:
            return None
        shot = self.path / str(name)
        return shot if shot.exists() else None


@dataclass
class Issue:
    """A validation problem. `level` is 'error' (blocks) or 'warning' (nags)."""

    level: str
    where: str
    message: str
    fix: str = ""


@dataclass
class LoadResult:
    bots: list[Bot] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


def bot_dirs() -> list[Path]:
    """Every root-level folder holding a bot.yaml, one per student chatbot."""
    return sorted(
        p
        for p in ROOT.iterdir()
        if p.is_dir()
        and not p.name.startswith((".", "_"))
        and p.name not in SKIP_DIRS
        and (p / "bot.yaml").exists()
    )


def load_bots() -> LoadResult:
    """Parse every <slug>/bot.yaml. Parse failures become issues, not crashes."""
    result = LoadResult()
    for path in bot_dirs():
        manifest = path / "bot.yaml"
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            result.issues.append(
                Issue(
                    "error",
                    f"{path.name}/bot.yaml",
                    f"this file isn't valid YAML: {exc}",
                    "Usually a missing quote, a tab character, or bad indentation.",
                )
            )
            continue
        if not isinstance(data, dict):
            result.issues.append(
                Issue(
                    "error",
                    f"{path.name}/bot.yaml",
                    "the file is empty or isn't a set of key: value pairs",
                    "Start from _pages/template/bot.yaml.",
                )
            )
            continue

        readme_path = path / "README.md"
        readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        result.bots.append(Bot(slug=path.name, path=path, data=data, readme=readme))
    return result


def sort_bots(bots: list[Bot]) -> list[Bot]:
    """Newest cohort first, then live bots, then by name."""
    return sorted(
        bots,
        key=lambda b: (
            b.is_example,
            -(b.year or 0),
            b.name.lower(),
        ),
    )


def collect_students(bots: list[Bot]) -> dict[str, dict]:
    """Fold authors across all bots into one record per GitHub handle."""
    students: dict[str, dict] = {}
    for bot in sort_bots(bots):
        for author in bot.authors:
            handle = str(author.get("github", "")).strip().lstrip("@")
            if not handle:
                continue
            record = students.setdefault(
                handle.lower(),
                {
                    "handle": handle,
                    "name": str(author.get("name", handle)),
                    "grad_year": author.get("grad_year"),
                    "is_example": bot.is_example,
                    "contributions": [],
                },
            )
            if not bot.is_example:
                record["is_example"] = False
            if author.get("grad_year") and not record.get("grad_year"):
                record["grad_year"] = author["grad_year"]
            record["contributions"].append(
                {
                    "bot": bot,
                    "role": str(author.get("role", "")),
                    "learned": str(author.get("learned", "")).strip(),
                }
            )
    return dict(sorted(students.items(), key=lambda kv: kv[1]["name"].lower()))


# -- tiny terminal helpers ---------------------------------------------------

_USE_COLOR = sys.stdout.isatty()


def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def red(t: str) -> str:
    return paint(t, "31")


def green(t: str) -> str:
    return paint(t, "32")


def yellow(t: str) -> str:
    return paint(t, "33")


def bold(t: str) -> str:
    return paint(t, "1")


def dim(t: str) -> str:
    return paint(t, "2")
