#!/usr/bin/env python
"""Fetch an arXiv paper's LaTeX SOURCE and report the files to read, in reading order.

Reading the source instead of the PDF is the right move (idea from
github.com/karpathy/nanochat/blob/master/.claude/skills/read-arxiv-paper/SKILL.md): it is the
authors' own text, so sections, cross-references and equations arrive exact instead of degraded
by text extraction, and two-column layout never enters the picture. Author comments survive too,
which occasionally say more than the prose.

This handles the fiddly parts so they do not have to be re-derived each time:

  * an id, an /abs/ URL, an /src/ URL or a bare arXiv link all resolve to the same download
  * a submission may be a .tar.gz, a lone gzipped .tex, or PDF-only (older or opted-out
    papers) -- PDF-only is reported so the caller falls back to pdf2md.py rather than silently
    reading nothing
  * the entrypoint is the .tex that declares \\documentclass, not whatever is called main.tex
  * \\input/\\include children are listed in the order the entrypoint pulls them in, which is
    the order a person reads them

    uv run --with requests python fetch_arxiv.py 2104.03437
    uv run --with requests python fetch_arxiv.py https://arxiv.org/abs/2104.03437
"""
import argparse, gzip, re, shutil, sys, tarfile, urllib.request
from pathlib import Path

CACHE = Path.home() / '.cache' / 'claude-papers'


def arxiv_id(s):
  s = s.strip().rstrip('/')
  m = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', s)
  if m:
    return m.group(1)
  m = re.search(r'([a-z-]+/\d{7})', s)       # old style, e.g. cs.CV/0701001
  if m:
    return m.group(1)
  raise SystemExit(f'cannot parse an arXiv id from {s!r}')


def fetch(aid, force=False):
  d = CACHE / aid.replace('/', '_')
  d.mkdir(parents=True, exist_ok=True)
  blob = d / 'source'
  if force or not blob.exists() or blob.stat().st_size == 0:
    url = f'https://arxiv.org/src/{aid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as r, open(blob, 'wb') as f:
      shutil.copyfileobj(r, f)
  return d, blob


def unpack(d, blob):
  src = d / 'src'
  head = blob.open('rb').read(5)
  if head.startswith(b'%PDF'):
    return None                              # no LaTeX source available
  if src.exists():
    shutil.rmtree(src)
  src.mkdir()
  try:
    with tarfile.open(blob) as t:
      t.extractall(src)
    return src
  except tarfile.ReadError:
    pass
  try:                                       # a lone gzipped .tex
    (src / 'main.tex').write_bytes(gzip.decompress(blob.read_bytes()))
    return src
  except Exception:
    return None


def order_tex(src):
  tex = sorted(src.rglob('*.tex'))
  entry = None
  for f in tex:
    try:
      if '\\documentclass' in f.read_text(errors='ignore'):
        entry = f
        break
    except Exception:
      continue
  if entry is None:
    return tex, None
  body = entry.read_text(errors='ignore')
  order, seen = [entry], {entry}
  for m in re.finditer(r'\\(?:input|include|subfile)\s*\{([^}]+)\}', body):
    stem = m.group(1).strip()
    for cand in (src / stem, src / (stem + '.tex')):
      hit = cand if cand.exists() else None
      if hit is None:
        hit = next((f for f in tex if f.stem == Path(stem).stem and f not in seen), None)
      if hit and hit not in seen:
        order.append(hit); seen.add(hit)
        break
  order += [f for f in tex if f not in seen]
  return order, entry


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('paper', help='arXiv id or URL')
  ap.add_argument('--force', action='store_true', help='re-download')
  a = ap.parse_args()
  aid = arxiv_id(a.paper)
  d, blob = fetch(aid, a.force)
  print(f'arXiv {aid}   source {blob.stat().st_size/1e6:.1f} MB   cache {d}')
  src = unpack(d, blob)
  if src is None:
    print('NO LATEX SOURCE (PDF-only submission).')
    print(f'  fall back to:  curl -sL https://arxiv.org/pdf/{aid} -o {d}/paper.pdf && '
          f'uv run --with pymupdf python ~/.claude/skills/read-paper/pdf2md.py {d}/paper.pdf '
          f'-o {d}/paper.md')
    return 2
  order, entry = order_tex(src)
  if not order:
    print('unpacked, but no .tex found -- inspect', src)
    return 2
  print(f'entrypoint: {entry.relative_to(src) if entry else "(none found)"}')
  print(f'{len(order)} tex file(s), in reading order -- Read them in this order:')
  for f in order:
    print(f'  {f}   ({f.stat().st_size//1024} KB)')
  bib = list(src.rglob('*.bbl')) + list(src.rglob('*.bib'))
  if bib:
    print(f'bibliography: {bib[0]}')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
