from flask import Flask, request, render_template_string, abort
import requests
import secrets
import time
import os

app = Flask(__name__)

# ========================
# 🏠 動作確認
# ========================
@app.route("/")
def home():
    return "Flask is running!"

# ========================
# 🔧 設定
# ========================
SITE_KEY = os.environ.get("SITE_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")

# ngrok URL（固定でOK）
NGROK_URL = "https://danna-choicer-jestingly.ngrok-free.dev"

# 👇 重要：全部これに統一
DOMAIN = NGROK_URL

API_SECRET = os.environ.get("API_SECRET")

TOKEN_EXPIRE = 300

# ========================
# 🔑 トークン管理
# ========================
TOKENS = {}

# ========================
# 🌐 HTML
# ========================
HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>サーバー認証</title>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>
</head>
<body style="font-family:sans-serif;text-align:center;margin-top:50px;">

<h2>サーバー参加認証</h2>
<p>このページはDiscordサーバーの自動認証用です。</p>

<form method="POST">
<div class="cf-turnstile" data-sitekey="{{ site_key }}"></div>
<br>
<button type="submit">認証する</button>
</form>

</body>
</html>
"""

SUCCESS = "<h2>✅ 認証完了！このページは閉じてOK</h2>"
FAIL = "<h2>❌ 認証失敗</h2>"

# ========================
# 🔑 トークン発行API
# ========================
@app.route("/api/create_token", methods=["POST"])
def create_token():
    data = request.get_json()

    if not data or "user_id" not in data:
        return {"error": "user_id missing"}, 400

    token = secrets.token_urlsafe(32)

    TOKENS[token] = {
        "user_id": data["user_id"],
        "time": time.time()
    }

    print("✅ TOKEN:", token)

    return {"url": f"{DOMAIN}/verify/{token}"}


# ========================
# 🔐 Discord側にロール付与API（超重要）
# ========================
@app.route("/api/verify", methods=["POST"])
def verify_api():
    data = request.get_json()

    if data.get("secret") != API_SECRET:
        return {"error": "unauthorized"}, 403

    user_id = int(data["user_id"])

    print("✅ VERIFY API CALLED:", user_id)

    # 👉 ここはBot側で処理される（既に実装済み）
    return {"status": "ok"}


# ========================
# 🌐 認証ページ
# ========================
@app.route("/verify/<token>", methods=["GET", "POST"])
def verify(token):

    data = TOKENS.get(token)
    if not data:
        return abort(404)

    # 期限チェック
    if time.time() - data["time"] > TOKEN_EXPIRE:
        TOKENS.pop(token, None)
        return "リンク期限切れ", 403

    if request.method == "GET":
        return render_template_string(HTML, site_key=SITE_KEY)

    # CAPTCHA
    captcha = request.form.get("cf-turnstile-response")

    res = requests.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data={
            "secret": SECRET_KEY,
            "response": captcha
        }
    ).json()

    if not res.get("success"):
        return FAIL

    user_id = data["user_id"]

    # ========================
    # 🔥 Botに通知（最重要）
    # ========================
    try:
        r = requests.post(
            f"{NGROK_URL}/api/verify",
            json={
                "user_id": user_id,
                "secret": API_SECRET
            },
            timeout=5
        )

        print("VERIFY STATUS:", r.status_code)

        if r.status_code != 200:
            return "<h2>❌ 認証失敗（APIエラー）</h2>"

    except Exception as e:
        print("❌ ERROR:", e)
        return "<h2>❌ 認証失敗（通信エラー）</h2>"

    TOKENS.pop(token, None)

    return SUCCESS


# ========================
# 🚀 起動
# ========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
