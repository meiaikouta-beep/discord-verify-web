#!/usr/bin/env bash
set -euo pipefail

OUT="/root/casino-source-bundle.tar.gz"
STAGE="$(mktemp -d /root/casino-source-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/sources" "$STAGE/metadata"

mapfile -t SERVICES < <(systemctl list-unit-files --type=service --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'games|party|hub|chiikawa|atto1' || true)
: > "$STAGE/metadata/services.txt"
declare -A DIRS=()
for service in "${SERVICES[@]}"; do
  wd="$(systemctl show "$service" -p WorkingDirectory --value 2>/dev/null || true)"
  exec_start="$(systemctl show "$service" -p ExecStart --value 2>/dev/null || true)"
  user="$(systemctl show "$service" -p User --value 2>/dev/null || true)"
  printf '%s\n  WorkingDirectory=%s\n  ExecStart=%s\n  User=%s\n' "$service" "$wd" "$exec_start" "$user" >> "$STAGE/metadata/services.txt"
  [[ "$wd" == /opt/* && -d "$wd" ]] && DIRS["$wd"]=1
done

for dir in /opt/games-hub /opt/games-party /opt/atto1 /opt/*chiikawa* /opt/*casino* /opt/*boat*; do
  [[ -d "$dir" ]] && DIRS["$dir"]=1
done

if [[ ${#DIRS[@]} -eq 0 ]]; then
  echo "対象ソースが見つかりませんでした。" >&2
  exit 1
fi

for dir in "${!DIRS[@]}"; do
  name="${dir#/}"
  name="${name//\//__}"
  dest="$STAGE/sources/$name"
  mkdir -p "$dest"
  tar -C "$dir" \
    --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='.cache' \
    --exclude='*.sqlite' --exclude='*.sqlite3' --exclude='*.db' --exclude='*.db-*' \
    --exclude='*.env' --exclude='.env*' --exclude='*.pem' --exclude='*.key' \
    --exclude='*.log' --exclude='logs' --exclude='backups' --exclude='uploads' \
    --exclude='*.mp3' --exclude='*.mp4' --exclude='*.webm' \
    -cf - . | tar -C "$dest" -xf -
done

python3 - "$STAGE" <<'PY'
import os, re, sqlite3, sys
from pathlib import Path

stage = Path(sys.argv[1])
schema = []
for root in (Path('/opt'), Path('/root')):
    if not root.exists():
        continue
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.db', '.sqlite', '.sqlite3'}:
            continue
        try:
            con = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
            row = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='points'").fetchone()
            if row:
                cols = con.execute('PRAGMA table_info(points)').fetchall()
                schema.append(f'PATH={p}\nCREATE={row[0]}\nCOLUMNS={cols}\n')
            con.close()
        except Exception:
            pass
(stage/'metadata'/'points-schema.txt').write_text('\n'.join(schema) or 'points table not found\n', encoding='utf-8')

keywords = re.compile(r'poker|ポーカー|roulette|ルーレット|baccarat|バカラ|南国|slot|スロット|boat|ボート|points', re.I)
matches = []
token = re.compile(r'(?<![A-Za-z0-9_-])(?:mfa\.[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,})(?![A-Za-z0-9_-])')
literal = re.compile(r'(?im)^([ \t]*(?:DISCORD_)?(?:BOT_)?(?:TOKEN|SECRET|PASSWORD|API_KEY)[ \t]*[:=][ \t]*)(["\']?)[^\r\n"\']+(["\']?)')
for p in (stage/'sources').rglob('*'):
    if not p.is_file():
        continue
    if p.stat().st_size > 3_000_000:
        p.unlink()
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    if keywords.search(text):
        matches.append(str(p.relative_to(stage)))
    redacted = token.sub('[REDACTED_DISCORD_TOKEN]', text)
    redacted = literal.sub(r'\1"[REDACTED]"', redacted)
    if redacted != text:
        p.write_text(redacted, encoding='utf-8')
(stage/'metadata'/'keyword-files.txt').write_text('\n'.join(matches)+'\n', encoding='utf-8')
PY

tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"
echo "作成完了: $OUT"
du -h "$OUT"
echo "このファイルにはDB行データ、.env、秘密鍵、音声、node_modulesを含めていません。"
