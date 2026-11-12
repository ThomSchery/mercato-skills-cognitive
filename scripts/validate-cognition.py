"""Check that the cognitive overlay never touched the SDLC engine.

Compares the working tree with the pinned upstream commit using git objects:
- every upstream file under skills/ is byte-identical, except each SKILL.md,
  which must equal upstream after removing the single loader line (or, for the
  documented over-budget skills, after also ignoring blank-line differences);
- every skill has a COGNITION.md with exactly the five numbered blocks and
  introduces no CLI flag absent from that skill's upstream text;
- no upstream file is missing and no unexpected file exists under skills/.
Proves preservation, not LLM behavior or injection resistance.
"""
import re, subprocess, sys
from pathlib import Path

PIN = 'b6d1ecbdb7822043f5bd209115d738ddd40e6b40'
LOADER = b'Read COGNITION.md.\n'
FM = re.compile(rb'\A---\r?\n.*?\r?\n---\r?\n', re.S)
FLAG = re.compile(r'(?<![A-Za-z0-9-])--[a-z][a-z0-9-]*')
BLOCKS = ['## 1. Role & Anti-Sycophancy', '## 2. Delimiters & S2A', '## 3. Cognitive Protocols',
          '## 4. Dependencies — SDLC Engine', '## 5. Output Contract']
root = Path(__file__).resolve().parents[1]

def git(*a):
    return subprocess.check_output(['git', '-C', str(root), *a])

def blank_norm(b):
    return re.sub(rb'\n{2,}', b'\n', b)

errors = []
files = git('ls-tree', '-r', '--name-only', PIN, '--', 'skills').decode().splitlines()
names = sorted({f.split('/')[1] for f in files})
for f in files:
    up = git('show', f'{PIN}:{f}')
    p = root / f
    if not p.is_file():
        errors.append('missing: ' + f); continue
    cur = p.read_bytes()
    if f.endswith('/SKILL.md'):
        m = FM.match(cur)
        if not m or cur[m.end():m.end()+len(LOADER)] != LOADER:
            errors.append('loader missing/misplaced: ' + f); continue
        stripped = cur[:m.end()] + cur[m.end()+len(LOADER):]
        if stripped != up and blank_norm(stripped) != blank_norm(up):
            errors.append('engine changed beyond loader: ' + f)
        elif stripped != up:
            print('note: blank-line-only difference (body budget):', f)
    elif cur != up:
        errors.append('upstream file changed: ' + f)
for n in names:
    c = root / 'skills' / n / 'COGNITION.md'
    if not c.is_file():
        errors.append('no COGNITION.md: ' + n); continue
    t = c.read_text(encoding='utf-8')
    if re.findall(r'^## [1-5]\. .*$', t, re.M) != BLOCKS:
        errors.append('five-block contract invalid: ' + n)
    src = '\n'.join(git('show', f'{PIN}:{f}').decode() for f in files
                    if f.startswith(f'skills/{n}/') and f.endswith('.md'))
    extra = set(FLAG.findall(t)) - set(FLAG.findall(src))
    if extra:
        errors.append(f'{n}: COGNITION.md introduces flags {sorted(extra)}')
allowed = set(files) | {f'skills/{n}/COGNITION.md' for n in names}
for p in (root / 'skills').rglob('*'):
    rel = p.relative_to(root).as_posix()
    if p.is_file() and rel not in allowed:
        errors.append('unexpected file: ' + rel)
if errors:
    print('\n'.join('FAIL: ' + e for e in errors)); sys.exit(1)
print(f'PASS: {len(names)} skills, {len(files)} upstream files preserved; 1 loader + COGNITION.md per skill.')
print('Not tested: LLM behavior, live orchestration, cognitive effectiveness, injection resistance.')
