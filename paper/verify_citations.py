import re
import os

paper_dir = r"E:\cogninet-6g\paper"
tex_path = os.path.join(paper_dir, "main.tex")
bib_path = os.path.join(paper_dir, "references.bib")

with open(tex_path, "r", encoding="utf-8") as f:
    tex = f.read()

with open(bib_path, "r", encoding="utf-8") as f:
    bib = f.read()

# Find all citations in main.tex
tex_cites = set()
for match in re.finditer(r'\\cite\{([^}]+)\}', tex):
    keys = [k.strip() for k in match.group(1).split(',')]
    for k in keys:
        if k:
            tex_cites.add(k)

# Find all bib entries in references.bib
bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))

print(f"Total unique citations in main.tex: {len(tex_cites)}")
print(f"Total entries in references.bib: {len(bib_keys)}")

missing_in_bib = tex_cites - bib_keys
if missing_in_bib:
    print(f"ERROR: Missing in bib ({len(missing_in_bib)}): {missing_in_bib}")
else:
    print("SUCCESS: All citations in main.tex exist in references.bib!")

unused_in_tex = bib_keys - tex_cites
if unused_in_tex:
    print(f"NOTICE: {len(unused_in_tex)} keys in references.bib not directly cited in tex: {unused_in_tex}")
else:
    print("SUCCESS: Every bib key is cited in main.tex!")

# Also check bibtex aux file or bbl file to verify compilation resolution
aux_path = os.path.join(paper_dir, "main.aux")
if os.path.exists(aux_path):
    with open(aux_path, "r", encoding="utf-8") as f:
        aux = f.read()
    cites_in_aux = set(re.findall(r'\\citation\{([^}]+)\}', aux))
    all_aux_cites = set()
    for c in cites_in_aux:
        for k in c.split(','):
            all_aux_cites.add(k.strip())
    print(f"Citations resolved in aux: {len(all_aux_cites)}")
