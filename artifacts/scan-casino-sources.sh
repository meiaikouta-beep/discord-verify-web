#!/usr/bin/env bash
set -euo pipefail

OUT=/root/casino-source-scan.txt
exec > >(tee "$OUT") 2>&1

echo '=== relevant services ==='
mapfile -t SERVICES < <(systemctl list-unit-files --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'games|party|hub|chiikawa|atto1' || true)
declare -A DIRS=()
for service in "${SERVICES[@]}"; do
  wd="$(systemctl show "$service" -p WorkingDirectory --value 2>/dev/null || true)"
  start="$(systemctl show "$service" -p ExecStart --value 2>/dev/null || true)"
  printf '%s\n  WorkingDirectory=%s\n  ExecStart=%s\n' "$service" "$wd" "$start"
  [[ "$wd" == /opt/* && -d "$wd" ]] && DIRS["$wd"]=1
done

for dir in /opt/games-hub /opt/games-party /opt/atto1 /opt/*chiikawa* /opt/*party* /opt/*hub*; do
  [[ -d "$dir" ]] && DIRS["$dir"]=1
done

echo
echo '=== source directories ==='
for dir in "${!DIRS[@]}"; do
  printf '%s  ' "$dir"
  du -sh "$dir" 2>/dev/null | awk '{print $1}'
done

echo
echo '=== keyword source files ==='
PATTERN='poker|ポーカー|roulette|ルーレット|baccarat|バカラ|南国|slot|スロット|boat|ボート|points'
for dir in "${!DIRS[@]}"; do
  if command -v rg >/dev/null 2>&1; then
    rg -l -i --hidden --glob '!node_modules/**' --glob '!.git/**' --glob '!*.min.js' --glob '!*.map' --glob '!*.db' --glob '!*.sqlite*' --glob '!*.env' "$PATTERN" "$dir" 2>/dev/null || true
  else
    find "$dir" -type f \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' -o -name '*.ts' -o -name '*.py' -o -name '*.html' -o -name '*.json' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -size -3M -print0 2>/dev/null |
      xargs -0 grep -IilE "$PATTERN" 2>/dev/null || true
  fi
done | sort -u | while IFS= read -r file; do
  [[ -f "$file" ]] && stat -c '%s bytes  %n' "$file"
done

echo
echo '=== likely entry and UI files ==='
for dir in "${!DIRS[@]}"; do
  find "$dir" -maxdepth 3 -type f \( -name 'server.*' -o -name 'app.*' -o -name 'index.html' -o -name 'package.json' \) -not -path '*/node_modules/*' -printf '%s bytes  %p\n' 2>/dev/null || true
done | sort -u

echo
echo '=== points table database and schema (no rows) ==='
python3 - <<'PY'
import sqlite3
from pathlib import Path
for root in (Path('/opt'), Path('/root')):
    if not root.exists():
        continue
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.db','.sqlite','.sqlite3'}:
            continue
        try:
            con=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
            row=con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='points'").fetchone()
            if row:
                print('PATH=',p)
                print('CREATE=',row[0])
                print('COLUMNS=',con.execute('PRAGMA table_info(points)').fetchall())
            con.close()
        except Exception:
            pass
PY

echo
echo "保存先: $OUT"
