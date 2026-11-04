#!/usr/bin/env bash
set -euo pipefail

OUT=/root/casino-assets.tar.gz
STAGE="$(mktemp -d /root/casino-assets-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/files" "$STAGE/metadata"

copy_file() {
  local src="$1"
  [[ -f "$src" ]] || { echo "不足: $src" >&2; return 1; }
  local dst="$STAGE/files$src"
  mkdir -p "$(dirname "$dst")"
  cp -L "$src" "$dst"
}

ROOT=/opt/talksurvivor/chibi_lobby/client
ASSET="$ROOT/assets"

# 共通3D描画とバカラのカード。
copy_file "$ROOT/vendor/three.module.js"
while IFS= read -r -d '' f; do copy_file "$f"; done < <(find "$ROOT/cards" -maxdepth 2 -type f -name '*.png' -print0)

# 南国育ち。現行の埋め込み画面から参照されているファイルだけ。
for f in \
  pachi_cabinet_v8.png \
  butterfly_top_v8.png butterfly_mid_v8.png butterfly_bottom_v8.png \
  seven_aim.jpg \
  bgm_kokoro.mp3 bgm_banchou.mp3 bgm_yossha.mp3 bgm_miko.mp3 \
  bgm_nana.mp3 bgm_refrain.mp3 bgm_ai.mp3 \
  pachi_freeze_v54.mp3 pachi_zeb_v54.mp3 pachi_freeze_end_v54.mp3 \
  se_robot_chance.mp3 se_shakin.mp3 \
  ts_gauge_recover1.mp3 ts_kakakakaan.mp3 ts_super_mimo.mp3 \
  ts_v20_at_end.mp3 ts_v20_at_last7.mp3; do
  copy_file "$ASSET/$f"
done
for n in 0 1 2 3 4 5 6; do copy_file "$ASSET/cd_$n.png"; done

# ボートレースの本番演出音声、入口画像、選手データ。
for f in \
  br_bgm_final.mp3 br_bgm_yosen.mp3 \
  br_in_g1_final.mp3 br_in_g1_yosen.mp3 \
  br_in_ippan_final.mp3 br_in_ippan_yosen.mp3 \
  br_in_sg_final.mp3 br_in_sg_yosen.mp3 \
  br_race_loop.wav; do
  copy_file "$ROOT/$f"
done
copy_file "$ASSET/boatrace_opening.jpg"
copy_file /opt/talksurvivor/chibi_lobby/server/fan2604.txt

# 現在の公開経路を確認する。シンボリックリンクもたどる。
for root in /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/caddy /etc/apache2/sites-enabled; do
  [[ -d "$root" ]] || continue
  while IFS= read -r -d '' f; do
    if grep -Eqi 'talksurvivor\.online|games-hub|games-party|chibi|proxy_pass' "$f"; then
      dst="$STAGE/files$f"
      mkdir -p "$(dirname "$dst")"
      cp -L "$f" "$dst"
    fi
  done < <(find -L "$root" -maxdepth 2 -type f -size -1M -print0 2>/dev/null)
done

# ちいかわ本番を起動しているunitも、名前に依存せず内容から取得する。
for unit in /etc/systemd/system/*.service; do
  [[ -f "$unit" ]] || continue
  if grep -Eqi '/opt/talksurvivor|chibi_lobby' "$unit"; then
    dst="$STAGE/files$unit"
    mkdir -p "$(dirname "$dst")"
    cp -L "$unit" "$dst"
  fi
done

find "$STAGE/files" -type f -printf '%s bytes  %P\n' | sort -k2 > "$STAGE/metadata/included-files.txt"
tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"
echo "作成完了: $OUT"
du -h "$OUT"
echo '現行画面が実際に参照するカジノ・ボート素材だけを含みます。DB、秘密鍵、環境設定、ログ、旧バックアップは含めていません。'
