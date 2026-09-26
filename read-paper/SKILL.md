---
name: read-paper
description: Read a research paper properly - fetch its LaTeX source from arXiv and read that rather than the PDF (the authors' own text, with exact equations, sections and cross-references), falling back to a column-aware PDF extractor for non-arXiv or PDF-only papers; resolve the real arXiv id instead of recalling one, and always check whether there is released code. Use whenever a paper, preprint, arXiv link or PDF needs to be read, summarised, compared against an implementation, or checked for a codebase.
---

# Reading a paper

Read the SOURCE, not the PDF. A PDF is a rendering: text extraction from a two-column page
interleaves the columns, breaks sentences in half and turns equations into `(cid:NN)`. The
LaTeX source is what the authors wrote.

The arXiv-source idea is from Karpathy's `read-arxiv-paper` skill in nanochat
(github.com/karpathy/nanochat/blob/master/.claude/skills/read-arxiv-paper/SKILL.md).

## 1. Get the source

```bash
uv run --no-project python ~/.claude/skills/read-paper/fetch_arxiv.py <id-or-url>
```

Takes an id, an `/abs/` URL or an `/src/` URL. Downloads to `~/.cache/claude-papers/<id>/`
(skipped if already there), unpacks, finds the entrypoint by looking for `\documentclass`
rather than trusting a filename, and prints the `.tex` files **in the order the entrypoint
pulls them in**. Read them in that order.

What you get that a PDF cannot give: exact equations, real `\ref`/`\cite` structure, the
supplementary sections, and the authors' own `%` comments -- which occasionally reveal more
than the prose (the Aria Gen 2 Pilot source carries `% Show some photos? RGB? trajectory?`).

Exit status 2 means **no LaTeX source** -- older submissions and opt-outs are PDF-only. The
script prints the fallback command; do not silently read nothing.

## 2. Fallback: PDF only, or not on arXiv at all

Plenty of relevant work is not on arXiv -- RSS, older CVPR, most robotics conference
proceedings. Fetch from the proceedings site and use the bundled column-aware extractor:

```bash
uv run --no-project --with pymupdf python ~/.claude/skills/read-paper/pdf2md.py paper.pdf -o paper.md
```

It clips each column separately and concatenates, so paragraphs stay contiguous and in reading
order; column count is detected per page so title pages are not split wrongly. Measured on
DART (RSS 2014), same sentence:

| tool | output |
|---|---|
| markitdown | `TraditionalICP-basedapproachesneglectsomeinformation p(D|t)= p(D(u)|t)...` |
| `pdftotext -layout` | correct words, but the other column on the same line |
| `pdf2md.py` | the full paragraph, contiguous |

markitdown loses inter-word spacing entirely and interleaves columns -- never use it for a
paper. It stays useful for **docx, pptx, xlsx, html**. `pdftotext -layout` is an acceptable
third choice: spacing and unicode maths survive, but read whole paragraphs rather than trusting
line adjacency.

Sanity-check any extraction with `wc -w`. A real paper is thousands of words; a few hundred
means a scan or an HTML error page saved as `.pdf` -- check `file -b paper.pdf`.

## 3. Never trust a remembered arXiv id

Resolve it from the API. A recalled id is wrong often enough to waste a download and, worse, to
silently fetch a *different* paper with a plausible title:

```bash
python3 - <<'PY'
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
q = 'ti:"EXACT TITLE HERE"'
url = 'http://export.arxiv.org/api/query?' + urllib.parse.urlencode(
    {'search_query': q, 'max_results': 5})
x = ET.fromstring(urllib.request.urlopen(url, timeout=30).read())
NS = {'a': 'http://www.w3.org/2005/Atom'}
for e in x.findall('a:entry', NS):
    print(e.find('a:id', NS).text.rsplit('/', 1)[-1],
          ' '.join(e.find('a:title', NS).text.split())[:80])
PY
```

Confirm you got the right paper from the author line of the source, not from the id matching
your expectation.

## 4. Always report whether there is code

A method with a released implementation is worth far more than one without, so this is part of
reading the paper:

```bash
grep -rhoE "https?://[A-Za-z0-9./_-]*github[A-Za-z0-9./_-]*|github\.com/[A-Za-z0-9._/-]+|[a-z0-9-]+\.github\.io/[a-z0-9._/-]*" ~/.cache/claude-papers/<id>/src/ | sed 's/[.,)}\\]*$//' | sort -u
```

Then **verify each URL resolves** -- papers cite repos that were never published
(`tschmidt23/dart` is live, `tanner-schmidt/dart` 404s):

```bash
curl -sI --max-time 20 -o /dev/null -w '%{http_code}\n' <url>
```

If the grep is empty, check the project page or search `<first-author> <method> github` before
concluding there is none.

## 5. What to report back

- what the method actually optimises or predicts, in one or two sentences
- whether it is **learned** (needs training data, usually per-category) or
  **optimisation/geometric** (runs on a known asset) -- this often decides usability outright
- code: URL, whether it resolved, and language/framework if that affects adoption
- the one or two ideas that transfer, and explicitly what does **not**

Say plainly when a paper's approach cannot be used and why, rather than summarising it as if it
could be. Quote the source when a claim matters -- with the LaTeX in hand there is no reason to
paraphrase a number or an equation.

## Setup (idempotent, safe to re-run)

`--no-project` matters: without it, `uv run` inside a repo that has a `pyproject.toml` creates a `.venv` there and installs the project, which is a surprising side effect of reading a paper. `fetch_arxiv.py` needs only the standard library. `pdf2md.py` pulls PyMuPDF via
`uv run --with pymupdf` into a cached ephemeral env on first use. For the non-paper formats:

```bash
command -v markitdown >/dev/null 2>&1 \
  || uv tool install "markitdown[pdf]" 2>/dev/null \
  || pipx install "markitdown[pdf]" 2>/dev/null \
  || python3 -m pip install --user "markitdown[pdf]"
```

Install CLI tools user-level (`uv tool install` -> `~/.local/bin`, already on PATH), never into
a project environment: they are authoring tools, not dependencies of any repo. Note
`python3 -m venv` is unavailable on some machines (no `ensurepip`), hence the `uv`/`pipx`
preference.
