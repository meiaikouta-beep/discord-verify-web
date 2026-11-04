#!/usr/bin/env bash
set -euo pipefail

OUT=/root/casino-source-step2.tar.gz
STAGE="$(mktemp -d /root/casino-step2-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/files" "$STAGE/metadata"

copy_file() {
  local src="$1"
  [[ -f "$src" ]] || return 0
  local dst="$STAGE/files$src"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
}

copy_source_tree() {
  local root="$1"
  [[ -d "$root" ]] || return 0
  find "$root" -type f \
    \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' -o -name '*.ts' \
       -o -name '*.tsx' -o -name '*.jsx' -o -name '*.py' -o -name '*.html' \
       -o -name '*.css' -o -name '*.scss' -o -name '*.json' -o -name '*.toml' \
       -o -name '*.yaml' -o -name '*.yml' -o -name 'package.json' \
       -o -name 'package-lock.json' -o -name 'requirements.txt' \) \
    -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.venv/*' \
    -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -name '*.map' \
    -not -name '*.min.js' -size -4M -print0 |
    while IFS= read -r -d '' src; do copy_file "$src"; done
}

# 「ちいかわの森」の実体。本番 client/server のコードだけを取得する。
# 同階層に大量にある backup_* は対象外。
for root in \
  /opt/talksurvivor/chibi_lobby/client \
  /opt/talksurvivor/chibi_lobby/server \
  /opt/talksurvivor/chibi_lobby/bot \
  /opt/talksurvivor/chibi_lobby/tests \
  /opt/talksurvivor/chibi_lobby/tools; do
  copy_source_tree "$root"
done

# ゲームセンターの配信済み設定・入口。画像や音声はまだ取得しない。
for root in /var/www/games /opt/games-hub/web; do
  copy_source_tree "$root"
done

# カジノ機能とボートレースが参照するファイル名・サイズを確認するための一覧。
find /opt/talksurvivor/chibi_lobby/client /opt/talksurvivor/chibi_lobby/server \
  -type f -not -path '*/node_modules/*' -not -path '*/.git/*' \
  -not -path '*/.venv/*' -not -path '*/__pycache__/*' \
  -printf '%s bytes  %p\n' 2>/dev/null | sort -k2 > "$STAGE/metadata/chibi-current-files.txt"

find /var/www/games -maxdepth 4 -type f \
  -printf '%s bytes  %p\n' 2>/dev/null | sort -k2 > "$STAGE/metadata/hub-published-files.txt" || true

# ドメインから各サービスへの振り分けだけを保存する。証明書や鍵は取得しない。
if command -v rg >/dev/null 2>&1; then
  rg -n -i 'talksurvivor\.online|games-hub|games-party|chibi_lobby|proxy_pass|location ' \
    /etc/nginx /etc/caddy /etc/apache2 /etc/systemd/system \
    2>/dev/null > "$STAGE/metadata/routes.txt" || true
fi

# ソース中のカジノ・ボート関連箇所の索引。次に必要な画像・音声だけを選ぶために使う。
if command -v rg >/dev/null 2>&1; then
  rg -n -i 'roulette|ルーレット|baccarat|バカラ|南国|slot|スロット|boat.?race|ボート|casino|カジノ' \
    /opt/talksurvivor/chibi_lobby/client /opt/talksurvivor/chibi_lobby/server \
    2>/dev/null > "$STAGE/metadata/casino-references.txt" || true
fi

# 念のため文字列の秘密情報をマスクする。DB、環境設定、ログは最初から取得しない。
python3 - "$STAGE" <<'PY'
import re, sys
from pathlib import Path

stage = Path(sys.argv[1])
discord = re.compile(r'(?<![A-Za-z0-9_-])(?:mfa\.[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,})(?![A-Za-z0-9_-])')
literal = re.compile(r'''(?im)^([ \t]*(?:DISCORD_)?(?:BOT_)?(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY)[ \t]*[:=][ \t]*)(["']?)[^\r\n"']+(["']?)''')
for p in (stage / 'files').rglob('*'):
    if not p.is_file():
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    text = discord.sub('[REDACTED_DISCORD_TOKEN]', text)
    text = literal.sub(r'\1"[REDACTED]"', text)
    p.write_text(text, encoding='utf-8')
PY

tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"
echo "作成完了: $OUT"
du -h "$OUT"
echo '本番コードとファイル一覧だけです。画像、音声、DB、環境設定、ログ、バックアップは含めていません。'
