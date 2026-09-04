#!/usr/bin/env python
"""Extract a paper's text in READING ORDER, handling two-column layouts.

Why this exists: general-purpose converters flatten a two-column page line by line, so the two
columns interleave and every sentence is cut in half. Measured on DART (RSS 2014), markitdown
returned `TraditionalICP-basedapproachesneglectsomeinformation p(D|theta)= p(D(u)|theta)...` --
word spacing gone, both columns on one line, equations as (cid:NN). `pdftotext -layout` keeps
spacing and real unicode but still emits the columns side by side. Neither is readable.

Clipping each column separately and concatenating gives contiguous paragraphs in the order a
person reads them, which is what both a human and a model need.

Column count is detected per page from how many text blocks straddle the page midline, so
single-column pages (title pages, appendices) are not split wrongly.

    uv run --with pymupdf python pdf2md.py paper.pdf -o paper.md
"""
import argparse, sys
from pathlib import Path


def page_text(pg, cross_frac=0.30):
  import pymupdf
  r = pg.rect
  mid = (r.x0 + r.x1) / 2
  blocks = [b for b in pg.get_text('blocks') if (b[4] or '').strip()]
  if not blocks:
    return ''
  # a block "straddles" if it spans the midline by a real margin on both sides
  pad = 0.02 * r.width
  crossing = sum(1 for b in blocks if b[0] < mid - pad and b[2] > mid + pad)
  if crossing / len(blocks) > cross_frac:
    return pg.get_text('text', sort=True)            # single column (or full-width figures)
  out = []
  for clip in (pymupdf.Rect(r.x0, r.y0, mid, r.y1), pymupdf.Rect(mid, r.y0, r.x1, r.y1)):
    t = pg.get_text('text', clip=clip, sort=True).strip()
    if t:
      out.append(t)
  return '\n\n'.join(out)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument('pdf')
  ap.add_argument('-o', '--out', default='')
  ap.add_argument('--pages', default='', help='e.g. 1-8 (1-based, inclusive)')
  a = ap.parse_args()
  import pymupdf
  doc = pymupdf.open(a.pdf)
  lo, hi = 0, len(doc)
  if a.pages:
    parts = a.pages.split('-')
    lo = int(parts[0]) - 1
    hi = int(parts[-1])
  chunks = []
  for i in range(lo, min(hi, len(doc))):
    chunks.append(f'\n\n<!-- page {i+1} -->\n\n' + page_text(doc[i]))
  txt = ''.join(chunks)
  if a.out:
    Path(a.out).write_text(txt)
    print(f'{a.out}  {len(txt.split())} words, {min(hi,len(doc))-lo} pages')
  else:
    sys.stdout.write(txt)


if __name__ == '__main__':
  main()
