#!/usr/bin/env bash
set -euo pipefail

SRC=/opt/talksurvivor/chibi_lobby/client/index.html
OUT=/root/casino-source-step3.tar.gz
STAGE="$(mktemp -d /root/casino-step3-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

if [[ ! -f "$SRC" ]]; then
  echo "見つかりません: $SRC" >&2
  exit 1
fi

mkdir -p "$STAGE/files/opt/talksurvivor/chibi_lobby/client" "$STAGE/metadata"
cp "$SRC" "$STAGE/files/opt/talksurvivor/chibi_lobby/client/index.html"

# 配置時に必要になる現在のリバースプロキシとサービス定義。秘密鍵・環境設定は含めない。
for root in /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/caddy /etc/apache2/sites-enabled; do
  [[ -d "$root" ]] || continue
  find "$root" -maxdepth 2 -type f -size -1M -print0 |
    while IFS= read -r -d '' f; do
      if grep -Eqi 'talksurvivor\.online|games-hub|games-party|chibi|proxy_pass' "$f"; then
        dst="$STAGE/files$f"
        mkdir -p "$(dirname "$dst")"
        cp "$f" "$dst"
      fi
    done
done

for unit in /etc/systemd/system/games-hub.service /etc/systemd/system/games-party.service; do
  [[ -f "$unit" ]] || continue
  dst="$STAGE/files$unit"
  mkdir -p "$(dirname "$dst")"
  cp "$unit" "$dst"
done

sha256sum "$SRC" > "$STAGE/metadata/index.sha256"
tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"
echo "作成完了: $OUT"
du -h "$OUT"
echo '南国育ちの現行画面本体と、配置先確認用の公開設定だけを含みます。'
