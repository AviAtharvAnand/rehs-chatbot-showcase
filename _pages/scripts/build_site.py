#!/usr/bin/env python3
"""Build the static gallery: every <slug>/bot.yaml at the repo root -> site/.

    python _pages/scripts/build_site.py           # build into site/
    python _pages/scripts/build_site.py --serve   # build, then serve at :8000
    python _pages/scripts/build_site.py --base-url https://example.org/showcase/

Output, plain HTML, no JavaScript needed to read any of it:

    site/index.html                   the gallery
    site/bots/<slug>/index.html       one page per bot
    site/students/<handle>/index.html one page per student

site/ is wiped and regenerated every run. Never edit it by hand.
"""

from __future__ import annotations

import argparse
import html
import os
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

from _common import (  # noqa: E402
    SITE_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    bold,
    collect_students,
    dim,
    green,
    load_bots,
    red,
    sort_bots,
)

DEFAULT_BASE_URL = "https://nrp-nautilus.github.io/rehs-chatbot-showcase/"
#: Where the folders themselves live, so pages can link to the real code and manifests.
DEFAULT_REPO_URL = "https://github.com/nrp-nautilus/rehs-chatbot-showcase"


def render_markdown(text: str) -> str:
    """Bot READMEs -> HTML. Falls back to preformatted text if `markdown` isn't installed."""
    if not text.strip():
        return ""
    try:
        import markdown  # type: ignore
    except ImportError:
        return f"<pre class='raw-markdown'>{html.escape(text)}</pre>"
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )


def site_stats(bots: list, students: dict) -> dict:
    """Headline numbers count real cohort work, the reference entry is excluded."""
    real = [b for b in bots if not b.is_example]
    real_students = [s for s in students.values() if not s["is_example"]]
    years = sorted({b.year for b in real if b.year})
    return {
        "bots": len(real),
        "students": len(real_students),
        "deployed": len([b for b in real if "Deployment" in b.kinds]),
        "year_label": (
            str(years[0]) if len(years) == 1 else f"{years[0]}-{years[-1]}" if years else ""
        ),
    }


def copy_assets(bots: list) -> dict[str, str]:
    """Copy the stylesheet and every screenshot into site/assets/. Returns slug -> path."""
    assets = SITE_DIR / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STATIC_DIR / "style.css", assets / "style.css")
    for logo in STATIC_DIR.iterdir():
        if logo.suffix.lower() in {".svg", ".png"}:
            shutil.copy2(logo, assets / logo.name)

    shots: dict[str, str] = {}
    shots_dir = assets / "shots"
    shots_dir.mkdir(exist_ok=True)
    for bot in bots:
        shot = bot.screenshot
        if not shot:
            continue
        target = shots_dir / f"{bot.slug}{shot.suffix.lower()}"
        shutil.copy2(shot, target)
        shots[bot.slug] = f"assets/shots/{target.name}"
    return shots


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build(base_url: str, repo_url: str = DEFAULT_REPO_URL) -> int:
    loaded = load_bots()
    fatal = [i for i in loaded.issues if i.level == "error"]
    if fatal:
        print(red("Can't build the site, some entries don't parse:"))
        for issue in fatal:
            print(f"  {issue.where}: {issue.message}")
        print(dim("Run `make validate` for the full report."))
        return 1

    bots = sort_bots(loaded.bots)
    students = collect_students(bots)

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    shots = copy_assets(bots)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    base = base_url if base_url.endswith("/") else base_url + "/"
    repo = repo_url.rstrip("/")
    common = {
        "base_url": base,
        "repo_url_root": repo,
        "built_on": date.today().isoformat(),
        "stats": site_stats(bots, students),
    }

    write(
        SITE_DIR / "index.html",
        env.get_template("index.html.j2").render(
            **common,
            root="",
            page_title="REHS Chatbot Showcase",
            page_description=(
                "AI chatbots built and deployed on the National Research Platform by "
                "high school students in the SDSC REHS program."
            ),
            bots=bots,
            students=students,
            shots=shots,
            repo=repo,
            og_image=next((shots[b.slug] for b in bots if b.slug in shots), None),
        ),
    )

    bot_template = env.get_template("bot.html.j2")
    for bot in bots:
        write(
            SITE_DIR / "bots" / bot.slug / "index.html",
            bot_template.render(
                **common,
                root="../../",
                page_title=f"{bot.name} | REHS Chatbot Showcase",
                page_description=bot.tagline,
                bot=bot,
                source_url=f"{repo}/tree/main/{bot.slug}/src",
                k8s_url=f"{repo}/tree/main/{bot.slug}/k8s",
                k8s_blob=f"{repo}/blob/main/{bot.slug}/k8s",
                shot=shots.get(bot.slug),
                og_image=shots.get(bot.slug),
                body_html=render_markdown(bot.readme),
            ),
        )

    student_template = env.get_template("student.html.j2")
    for key, student in students.items():
        write(
            SITE_DIR / "students" / student["handle"] / "index.html",
            student_template.render(
                **common,
                root="../../",
                page_title=f"{student['name']} | REHS Chatbot Showcase",
                page_description=(
                    f"{student['name']} built AI chatbots on the National Research "
                    "Platform in the SDSC REHS program."
                ),
                student=student,
                shots=shots,
                repo=repo,
                og_image=next(
                    (
                        shots[c["bot"].slug]
                        for c in student["contributions"]
                        if c["bot"].slug in shots
                    ),
                    None,
                ),
            ),
        )
        # People type handles in any case; keep a lowercase alias when it differs.
        # Only when the key differs by more than case: on a case-insensitive
        # filesystem the two paths are the same, and the alias would clobber
        # the real page with a redirect to itself.
        if student["handle"].lower() != key:
            write(
                SITE_DIR / "students" / key / "index.html",
                f'<meta http-equiv="refresh" content="0; '
                f'url={base}students/{student["handle"]}/">',
            )

    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    write(SITE_DIR / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.txt\n")
    urls = [base]
    urls += [f"{base}bots/{b.slug}/" for b in bots]
    urls += [f"{base}students/{s['handle']}/" for s in students.values()]
    write(SITE_DIR / "sitemap.txt", "\n".join(urls) + "\n")

    print(green("Built site/"))
    print(
        f"  {bold(str(len(bots)))} bot page(s), "
        f"{bold(str(len(students)))} student page(s), "
        f"{bold(str(len(shots)))} screenshot(s)"
    )
    if not bots:
        print(dim("  (no chatbot folders yet, the gallery shows its empty state)"))
    print(dim(f"  base URL: {base}"))
    return 0


def serve(port: int = 8000) -> None:
    import http.server
    import socketserver

    os.chdir(SITE_DIR)
    print(green(f"Serving site/ at http://localhost:{port}   (ctrl-C to stop)"))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nbye")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the showcase gallery.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SHOWCASE_BASE_URL", DEFAULT_BASE_URL),
        help=f"public URL the site will live at (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--repo-url",
        default=os.environ.get("SHOWCASE_REPO_URL", DEFAULT_REPO_URL),
        help="repo the chatbot folders live in, for source links",
    )
    parser.add_argument("--serve", action="store_true", help="serve site/ after building")
    args = parser.parse_args()

    code = build(args.base_url, args.repo_url)
    if code == 0 and args.serve:
        serve()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
