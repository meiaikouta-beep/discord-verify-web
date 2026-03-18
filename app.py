from flask import Flask, request, render_template_string
import requests
import os

app = Flask(__name__)

SITE_KEY = "0x4AAAAAACsw5njeX3Amm_bR"
SECRET_KEY = "0x4AAAAAACsw5jeV2woESqgaF56JIm9OP9Y"

# ここは今のBot側 ngrok URL にする
BOT_VERIFY_API_URL = "https://danna-choicer-jestingly.ngrok-free.dev/api/verify"

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>認証</title>
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"></script>
<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #000000, #111111, #1a1a1a);
    font-family: sans-serif;
}
.container {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    text-align: center;
    width: 90%;
    max-width: 380px;
}
h2 {
    margin-bottom: 10px;
}
.desc {
    color: #666;
    font-size: 14px;
    margin-bottom: 18px;
}
#turnstile-box {
    margin: 20px 0;
    display: flex;
    justify-content: center;
}
#error-msg {
    color: red;
    font-size: 13px;
    margin-top: 10px;
    white-space: pre-wrap;
    min-height: 18px;
}
button {
    margin-top: 20px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    background: #667eea;
    color: white;
    font-size: 16px;
    cursor: pointer;
}
button:hover {
    background: #5563d6;
}
</style>
</head>
<body>
<div class="container">
    <h2>本人確認</h2>
    <p class="desc">数秒で完了します</p>

    <form method="POST">
        <input type="hidden" name="user_id" value="{{ user_id }}">
        <div id="turnstile-box"></div>
        <div id="error-msg"></div>
        <button type="submit">認証する</button>
    </form>
</div>

<script>
window.onload = function () {
    try {
        turnstile.render('#turnstile-box', {
            sitekey: '{{ site_key }}',
            callback: function(token) {
                console.log('Turnstile success:', token);
            },
            'error-callback': function(code) {
                console.log('Turnstile error:', code);
                document.getElementById('error-msg').textContent =
                    'CAPTCHAの読み込みに失敗しました: ' + code;
            },
            'expired-callback': function() {
                document.getElementById('error-msg').textContent =
                    '認証の有効期限が切れました。再読み込みしてください。';
            }
        });
    } catch (e) {
        console.log('Turnstile render exception:', e);
        document.getElementById('error-msg').textContent =
            'CAPTCHA描画例外: ' + e;
    }
};
</script>
</body>
</html>
"""

SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>認証成功</title>
<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #101010;
    font-family: sans-serif;
}
.box {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    text-align: center;
}
h2 {
    color: #4CAF50;
}
p {
    color: #666;
}
</style>
</head>
<body>
<div class="box">
    <h2>✅ 認証成功！</h2>
    <p>この画面は閉じてOKです</p>
</div>
</body>
</html>
"""

FAIL_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>認証失敗</title>
<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #101010;
    font-family: sans-serif;
}
.box {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    text-align: center;
}
h2 {
    color: #e53935;
}
p {
    color: #666;
}
</style>
</head>
<body>
<div class="box">
    <h2>❌ 認証失敗</h2>
    <p>もう一度お試しください</p>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return "Flask is running!"

@app.route("/verify", methods=["GET", "POST"])
def verify_page():
    if request.method == "GET":
        user_id = request.args.get("user_id")
        print("🔥 VERIFY PAGE GET")
        print("user_id:", user_id)

        if not user_id:
            return "user_id がありません", 400

        return render_template_string(HTML, site_key=SITE_KEY, user_id=user_id)

    try:
        user_id = request.form.get("user_id")
        token = request.form.get("cf-turnstile-response")

        print("🔥 VERIFY PAGE POST")
        print("user_id:", user_id)
        print("token exists:", bool(token))

        if not user_id:
            return "user_id がありません", 400

        if not token:
            return "Turnstile token がありません", 400

        turnstile_res = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": SECRET_KEY,
                "response": token
            },
            timeout=10
        )

        turnstile_json = turnstile_res.json()
        print("🔥 Turnstile verify result:", turnstile_json)

        if not turnstile_json.get("success"):
            print("❌ Turnstile失敗")
            return FAIL_HTML, 400

        bot_res = requests.post(
            BOT_VERIFY_API_URL,
            json={"user_id": int(user_id)},
            timeout=10
        )

        print("🔥 Bot API status:", bot_res.status_code)
        print("🔥 Bot API response:", bot_res.text)

        if bot_res.status_code != 200:
            print("❌ Bot API失敗")
            return FAIL_HTML, 500

        return SUCCESS_HTML

    except Exception as e:
        print("❌ VERIFY PAGE ERROR:", e)
        return FAIL_HTML, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)




