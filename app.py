from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

SITE_KEY = "0x4AAAAAACsw5njeX3Amm_bR"
SECRET_KEY = "0x4AAAAAACsw5jeV2woESqgaF56JIm9OP9Y"

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>認証</title>

<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>

<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    background: linear-gradient(135deg, #667eea, #764ba2);
    font-family: sans-serif;
}

.container {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    text-align: center;
    width: 90%;
    max-width: 350px;
}

h2 {
    margin-bottom: 15px;
}

.desc {
    color: #888;
    font-size: 14px;
    margin-bottom: 20px;
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
    transition: 0.2s;
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
        <div class="cf-turnstile" data-sitekey="{{ site_key }}"></div>
        <button type="submit">認証する</button>
    </form>
</div>

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
    background: #f5f7fa;
    font-family: sans-serif;
}

.box {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
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
<h2 style="text-align:center; color:red;">❌ 認証失敗</h2>
<p style="text-align:center;">もう一度お試しください</p>
"""

@app.route("/")
def home():
    return "Flask is running!"

@app.route("/verify", methods=["GET", "POST"])
def verify():
    user_id = request.args.get("user_id")

    if request.method == "POST":
        token = request.form.get("cf-turnstile-response")

        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": SECRET_KEY,
                "response": token
            }
        ).json()

        if response.get("success"):
            print(f"認証成功 user_id={user_id}")
            return SUCCESS_HTML
        else:
            return FAIL_HTML

    return render_template_string(HTML, site_key=SITE_KEY)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
