#!/usr/bin/env bash
set -euo pipefail

OUT=/root/casino-source-step1.tar.gz
STAGE="$(mktemp -d /root/casino-step1-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/files" "$STAGE/metadata"

copy_file() {
  local src="$1"
  [[ -f "$src" ]] || return 0
  local dst="$STAGE/files$src"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

# 既知の小さいサーバー・UIソース
for src in \
  /opt/games-hub/server.cjs /opt/games-hub/mypage.cjs \
  /opt/games-party/server.cjs /opt/games-party/poker.cjs \
  /opt/games-party/public/index.html /opt/games-party/public/party.js \
  /opt/games-party/public/poker-ui.js; do
  copy_file "$src"
done

for root in /opt/games-hub /opt/games-party; do
  [[ -d "$root" ]] || continue
  find "$root" -maxdepth 4 -type f \
    \( -name '*.cjs' -o -name '*.mjs' -o -name '*.js' -o -name '*.ts' -o -name '*.html' -o -name '*.css' -o -name 'package.json' \) \
    -not -path '*/node_modules/*' -not -path '*/.git/*' -not -name '*.min.js' -not -name '*.map' -size -3M -print0 |
    while IFS= read -r -d '' src; do copy_file "$src"; done
done

# サービス名に現れない「ちいかわ」側を /opt 全体からゲーム名で特定
PATTERN='poker|ポーカー|roulette|ルーレット|baccarat|バカラ|南国|slot|スロット|boat|ボート'
if command -v rg >/dev/null 2>&1; then
  rg -l -i --hidden \
    --glob '!node_modules/**' --glob '!.git/**' --glob '!logs/**' \
    --glob '!*.min.js' --glob '!*.map' --glob '!*.db' --glob '!*.sqlite*' --glob '!*.env' \
    "$PATTERN" /opt 2>/dev/null | while IFS= read -r src; do
      [[ -f "$src" && $(stat -c '%s' "$src") -lt 3000000 ]] && copy_file "$src"
    done
fi

find /opt -maxdepth 3 -type d -printf '%p\n' 2>/dev/null | sort > "$STAGE/metadata/opt-directories.txt"
find /opt/games-hub /opt/games-party -maxdepth 4 -type f -not -path '*/node_modules/*' -printf '%s bytes  %p\n' 2>/dev/null | sort -k2 > "$STAGE/metadata/file-inventory.txt"

python3 - "$STAGE" <<'PY'
import re, sys
from pathlib import Path
stage=Path(sys.argv[1])
token=re.compile(r'(?<![A-Za-z0-9_-])(?:mfa\.[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,})(?![A-Za-z0-9_-])')
literal=re.compile(r'''(?im)^([ \t]*(?:DISCORD_)?(?:BOT_)?(?:TOKEN|SECRET|PASSWORD|API_KEY)[ \t]*[:=][ \t]*)(["']?)[^\r\n"']+(["']?)''')
for p in (stage/'files').rglob('*'):
    if not p.is_file(): continue
    try: text=p.read_text(encoding='utf-8')
    except Exception: continue
    text=token.sub('[REDACTED_DISCORD_TOKEN]',text)
    text=literal.sub(r'\1"[REDACTED]"',text)
    p.write_text(text,encoding='utf-8')
PY

tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"
echo "作成完了: $OUT"
du -h "$OUT"
echo 'DB、画像、音声、node_modules、環境設定、ログは含めていません。'
