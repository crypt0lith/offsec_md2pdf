#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<4.0"
# dependencies = [
#   "markdown",
#   "pygments",
#   "pymdown-extensions",
#   "pyyaml",
#   "weasyprint",
# ]
# ///
import datetime
import re
import sys
import urllib.parse
from collections import ChainMap
from pathlib import Path

OSID_RE = re.compile(r"(?:OS-)?(\d+)", re.I)
RGB_RE = re.compile(r"#?([a-f0-9]{3}|[a-f0-9]{6})", re.I)

LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
PROTOCOL_RE = re.compile(r"^[a-z][a-z0-9+.\-]*:", re.I)

CERTS = {
    "OSCP": "OffSec Certified Professional",
    "OSWP": "OffSec Wireless Professional",
    "OSWA": "OffSec Web Assessor",
    "OSDA": "OffSec Defense Analyst",
    "OSWE": "OffSec Web Expert",
    "OSEP": "OffSec Experienced Penetration Tester",
    "OSED": "OffSec Exploit Developer",
    "OSEE": "OffSec Exploitation Expert",
    "OSIR": "OffSec Incident Responder",
    "OSTH": "OffSec Threat Hunter",
}
REPORT_RE = re.compile(
    r"(?P<cert>OS(?:%s))(?:-(?P<osid>OS-\d+))?" % "|".join(k[2:] for k in CERTS)
)

DEFAULT_ACCENT = "#a76bf9"
DEFAULT_BACKGROUND = "#0e1116"

CSS_PATH = Path(__file__).resolve().parent / "style.css"


def infer_candidate_from_path(path: Path):
    m = REPORT_RE.match(path.stem)
    if not m:
        return {}
    return {k: v for k, v in m.groupdict().items() if v is not None}


def osid_normalize(value):
    m = OSID_RE.fullmatch(value.strip())
    if not m:
        raise ValueError(value)
    return f"OS-{m.group(1)}"


def normalize_rgb(value):
    m = RGB_RE.fullmatch(value.strip())
    if not m:
        raise ValueError(value)
    digits = m.group(1).lower()
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    return f"#{digits}"


def parse_frontmatter(raw):
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw

    import yaml

    try:
        fm = yaml.safe_load(raw[3:end]) or {}
    except yaml.YAMLError as e:
        raise RuntimeError(f"could not parse YAML frontmatter: {e}") from e

    if not isinstance(fm, dict):
        fm = {}
    body = raw[end + 4 :].lstrip("\n")
    fm = {k.casefold(): v for k, v in fm.items()}
    return fm, body


def rewrite_links(md, *, self_basename, normalize_slugs):
    from markdown.extensions.toc import slugify

    def repl(m):
        text, target = m.group(1), m.group(2)
        if "#" not in target:
            return m.group(0)
        # external url with fragment; ignore
        head = target.split("#", 1)[0]
        if PROTOCOL_RE.match(head):
            return m.group(0)

        fname, _, anchor = target.partition("#")
        if fname:
            if fname != self_basename:
                raise ValueError(
                    f"link references foreign file: `[{text}]({target})`; "
                    f"expected filename {self_basename!r}, got {fname!r}"
                )
            target = "#" + anchor

        if normalize_slugs and target.startswith("#"):
            decoded = urllib.parse.unquote(target[1:])
            target = "#" + slugify(decoded, "-")

        return f"[{text}]({target})"

    return LINK_RE.sub(repl, md)


def resolve_images(md, *, content_dir):
    def repl(m):
        alt, src = m.group(1), m.group(2)
        if PROTOCOL_RE.match(src):
            return m.group(0)

        as_given = (content_dir / src).resolve()
        if as_given.is_file():
            return f"![{alt}]({as_given.as_posix()})"

        basename = urllib.parse.unquote(Path(src).name)
        flat = content_dir / basename
        if flat.is_file():
            return f"![{alt}]({flat.as_posix()})"

        return (
            f'<div class="img-placeholder">'
            f"Missing image: <code>{basename}</code>"
            f"</div>"
        )

    return IMG_RE.sub(repl, md)


def render_html(body_md, *, cert, email, osid, date):
    if not isinstance(cert, str):
        raise TypeError(f"expected str, got {cert.__class__.__name__!r} instead")
    cert = cert.upper()
    if cert not in CERTS:
        raise ValueError(f"invalid cert name: {cert!r}")

    longname = CERTS[cert]

    import markdown
    from pygments.formatters import HtmlFormatter

    md = markdown.Markdown(
        extensions=[
            "extra",
            "codehilite",
            "toc",
            "sane_lists",
            "pymdownx.superfences",
            "pymdownx.tilde",
        ],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "css_class": "codehilite",
                "linenums": False,
            },
            "toc": {"toc_depth": "1-3", "anchorlink": False, "permalink": False},
        },
    )
    body_html = md.convert(body_md)
    toc_html = md.toc

    # codehilite wraps blocks in .codehilite; pymdownx.superfences uses .highlight
    formatter = HtmlFormatter(style="friendly")
    pygments_css = (
        formatter.get_style_defs(".codehilite")
        + "\n"
        + formatter.get_style_defs(".highlight")
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{cert} Exam Report -- {osid}</title>
<style>
{pygments_css}
</style>
</head>
<body>

<section class="title-page">
  <div class="title-band">
    <div class="title-main">{longname}<br>Exam Report</div>
    <div class="title-sub">{cert} Exam Report</div>
  </div>
  <div class="title-meta">
    <div class="meta-row"><span class="meta-label">Candidate</span><span class="meta-value">{email}</span></div>
    <div class="meta-row"><span class="meta-label">OSID</span><span class="meta-value">{osid}</span></div>
    <div class="meta-row"><span class="meta-label">Date</span><span class="meta-value">{date}</span></div>
  </div>
  <div class="title-footer">OffSec &mdash; Confidential</div>
</section>

<section class="toc-page">
  <h1 class="toc-title">Table of Contents</h1>
  <nav class="toc">
{toc_html}
  </nav>
</section>

<section class="body">
{body_html}
</section>

</body>
</html>
"""


def load_css(*, accent, background, header_text):
    if not CSS_PATH.is_file():
        raise FileNotFoundError(f"CSS file not found: {CSS_PATH}")
    css = CSS_PATH.read_text(encoding="utf-8")
    css = css.replace("__HEADER_TEXT__", header_text)
    # Append overrides last so they win the cascade
    css += (
        "\n:root {\n"
        f"    --accent: {accent};\n"
        f"    --title-bg: {background};\n"
        "}\n"
    )
    return css


def build_pdf(html, css, *, base_url, out_path):
    from weasyprint import CSS, HTML

    HTML(string=html, base_url=str(base_url)).write_pdf(
        str(out_path), stylesheets=[CSS(string=css)]
    )


def parse_args():
    import argparse

    def realpath_resolver(f, /):
        def wrapper(s):
            p = Path(s).resolve()
            if not f(p):
                err = "{} not found: {!r}".format(f.__name__.rpartition("_")[-1], s)
                raise argparse.ArgumentTypeError(err)
            return p

        return wrapper

    real_dirpath = realpath_resolver(Path.is_dir)
    real_filepath = realpath_resolver(Path.is_file)

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        argument_default=argparse.SUPPRESS,
        description="render an OffSec exam report markdown file to a PDF",
    )
    parser.add_argument(
        "file", metavar="FILE", type=real_filepath, help="markdown report file"
    )

    output_opts = parser.add_argument_group("output options")
    output_group = output_opts.add_mutually_exclusive_group()
    output_group.add_argument(
        "-o",
        "--outdir",
        dest="outdir",
        metavar="DIRNAME",
        type=real_dirpath,
        help="path to output directory",
    )
    output_group.add_argument(
        "-O",
        "--outfile",
        dest="outfile",
        metavar="FILE",
        type=Path,
        help="output PDF path",
    )

    frontmatter_desc = "each option, if not specified as an argument, can also be present in the markdown yaml frontmatter"

    candidate_opts = parser.add_argument_group(
        "candidate options",
        description=f"""\
        {frontmatter_desc}.
        '--cert' and '--osid' will be inferred from '--outfile' then FILE if unspecified via args / frontmatter,
        and if those path's basenames match the pattern '<CERT>-OS-<OSID>'""",
    )
    candidate_opts.add_argument(
        "--cert",
        dest="cert",
        metavar="CERT",
        choices=CERTS,
        type=str.upper,
        help="certification shortname, e.g. 'OSCP' (choices: %(choices)s)",
    )
    candidate_opts.add_argument(
        "--osid", dest="osid", help="candidate OSID, e.g. 'OS-12345'"
    )
    candidate_opts.add_argument("--email", dest="email", help="candidate email")

    render_opts = parser.add_argument_group(
        "rendering options", description=frontmatter_desc
    )
    render_opts.add_argument(
        "--accent",
        dest="accent",
        metavar="COLOR",
        type=normalize_rgb,
        help=f"accent color (default: {DEFAULT_ACCENT})",
    )
    render_opts.add_argument(
        "--background",
        dest="background",
        metavar="COLOR",
        type=normalize_rgb,
        help=f"title page background color (default: {DEFAULT_BACKGROUND})",
    )

    markdown_opts = parser.add_argument_group("markdown options")
    markdown_opts.add_argument(
        "--normalize-slugs",
        action="store_true",
        help="convert Obsidian-style anchor links to python-markdown slugs",
    )
    markdown_opts.add_argument(
        "--content-dir",
        metavar="DIRNAME",
        type=real_dirpath,
        help="base directory for relative image paths",
    )
    return parser.parse_args()


def main():
    ns = parse_args()

    md_path = ns.file
    out_path = getattr(ns, "outfile", None)

    raw = md_path.read_text(encoding="utf-8")

    try:
        frontmatter, body = parse_frontmatter(raw)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    outfile_info = {} if out_path is None else infer_candidate_from_path(out_path)
    file_info = infer_candidate_from_path(md_path)

    missing_in_ns = lambda k: f"--{k} not provided, {k!r} not found in YAML frontmatter"

    candidate_ns = ChainMap(vars(ns), frontmatter, outfile_info, file_info)
    candidate_info = {}
    for k in ["cert", "osid"]:
        try:
            candidate_info[k] = candidate_ns[k]
        except KeyError:
            if k == "cert":
                h1_re = re.compile(
                    r"# Off(?:Sec|ensive Security) (%s)"
                    % "|".join(
                        re.escape(v.removeprefix("OffSec ")) for v in CERTS.values()
                    ),
                    re.I,
                )
                try:
                    h1 = next(
                        m for m in map(h1_re.match, body.splitlines()) if m is not None
                    )
                    cert_long = h1.group(1).lower()
                    cert_short = next(
                        k for k, v in CERTS.items() if v.lower().endswith(cert_long)
                    )
                except StopIteration:
                    pass
                else:
                    candidate_info[k] = cert_short
                    continue
            print(
                f"error: {missing_in_ns(k)} and not inferrable from filename(s)",
                file=sys.stderr,
            )
            return 2
    try:
        candidate_info.update(email=candidate_ns["email"])
    except KeyError:
        print("error:", missing_in_ns("email"), file=sys.stderr)
        return 2
    osid = candidate_info.pop("osid")
    try:
        candidate_info.update(osid=osid_normalize(osid))
    except ValueError:
        print(f"error: invalid OSID: {osid!r}", file=sys.stderr)
        return 2

    candidate_info.update(date=datetime.date.today().isoformat())

    if out_path is None:
        out_dir = getattr(ns, "outdir", Path.cwd())
        out_path = out_dir / "{cert}-{osid}-Exam-Report.pdf".format_map(
            candidate_info
        )

    render_defaults = {"accent": DEFAULT_ACCENT, "background": DEFAULT_BACKGROUND}
    render_ns = ChainMap(vars(ns), frontmatter, render_defaults)
    render_info = {k: render_ns[k] for k in render_defaults}
    render_info.update(
        header_text="{cert} Exam Report -- {osid}".format_map(candidate_info)
    )

    try:
        body = rewrite_links(
            body,
            self_basename=md_path.name,
            normalize_slugs=getattr(ns, "normalize_slugs", False),
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    content_dir = getattr(ns, "content_dir", md_path.parent)

    body = resolve_images(body, content_dir=content_dir)
    html = render_html(body, **candidate_info)
    css = load_css(**render_info)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(html, css, base_url=content_dir, out_path=out_path)

    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
