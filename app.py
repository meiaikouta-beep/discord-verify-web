from flask import Flask, request, render_template_string, abort
import requests
import os
import secrets
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask is running!"

SITE_KEY = "0x4AAAAAACsw5njeX3Amm_bR"
SECRET_KEY = "0x4AAAAAACsw5jeV2woESqgaF56JIm9OP9Y"

# トークン管理（簡易DB）
TOKENS = {}

# 有効期限（秒）
TOKEN_EXPIRE = 300

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
<p style="font-size:12px;color:gray;">
パスワードや個人情報の入力は一切ありません。
</p>

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

# 🔑 トークン発行（Botから呼ぶ用）
@app.route("/api/create_token", methods=["POST"])
def create_token():
    user_id = request.json.get("user_id")

    token = secrets.token_urlsafe(32)
    TOKENS[token] = {
        "user_id": user_id,
        "time": time.time()
    }

    return {"url": f"https://discord-verify-web-7lod.onrender.com/verify/{token}"}


# 🌐 認証ページ
@app.route("/verify/<token>", methods=["GET", "POST"])
def verify(token):

    data = TOKENS.get(token)
    if not data:
        return abort(404)

    # 期限チェック
    if time.time() - data["time"] > TOKEN_EXPIRE:
        TOKENS.pop(token, None)
        return "期限切れ", 403

    if request.method == "GET":
        return render_template_string(HTML, site_key=SITE_KEY)

    # POST（CAPTCHA）
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

    # Bot側処理（同じサーバー推奨）
    requests.post(
        "https://discord-verify-web-7lod.onrender.com/verify/",
        json={"user_id": user_id}
    )

    TOKENS.pop(token, None)

    return SUCCESS


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)






