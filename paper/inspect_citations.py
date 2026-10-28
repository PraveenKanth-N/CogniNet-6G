import re
import os

paper_dir = r"E:\cogninet-6g\paper"
tex_path = os.path.join(paper_dir, "main.tex")
bib_path = os.path.join(paper_dir, "references.bib")

with open(tex_path, "r", encoding="utf-8") as f:
    tex = f.read()

with open(bib_path, "r", encoding="utf-8") as f:
    bib = f.read()

# Parse bib entries: key -> {title, author, year, journal/booktitle}
entries = {}
for entry in re.split(r'@\w+\{', bib)[1:]:
    key = entry.split(',')[0].strip()
    title_m = re.search(r'title\s*=\s*[\{"]([^"\}]+)[\}"]', entry, re.IGNORECASE)
    author_m = re.search(r'author\s*=\s*[\{"]([^"\}]+)[\}"]', entry, re.IGNORECASE)
    year_m = re.search(r'year\s*=\s*[\{"]([^"\}]+)[\}"]', entry, re.IGNORECASE)
    title = title_m.group(1) if title_m else ""
    author = author_m.group(1) if author_m else ""
    year = year_m.group(1) if year_m else ""
    entries[key] = {"title": title, "author": author, "year": year}

# Find all citations and show snippet
for match in re.finditer(r'([^.\n]{0,80}\\cite\{([^}]+)\}[^.\n]{0,80})', tex):
    snippet = match.group(1).replace('\n', ' ')
    keys = [k.strip() for k in match.group(2).split(',')]
    print(f"\nSNIPPET: {snippet}")
    for k in keys:
        if k in entries:
            print(f"  -> [{k}] ({entries[k]['year']}) {entries[k]['author'][:30]}... : {entries[k]['title'][:60]}")
        else:
            print(f"  -> [{k}] MISSING!")
