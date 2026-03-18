from flask import Flask, request, render_template_string
import requests
import threading
import os
app = Flask(__name__)

VERIFY_ROLE_REMOVE = 1483816333870366801
VERIFY_ROLE_ADD = 1482899395757473803

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
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>認証失敗</title>
</head>
<body>
    <h2 style="text-align:center; color:red;">❌ 認証失敗</h2>
    <p style="text-align:center;">もう一度お試しください</p>
</body>
</html>
"""

@app.route("/")
def home():
    return "Flask is running!"


# 認証画面
@app.route("/verify", methods=["GET", "POST"])
def verify_page():
    if request.method == "GET":
        user_id = request.args.get("user_id")
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

        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": SECRET_KEY,
                "response": token
            },
            timeout=10
        ).json()

        print("🔥 Turnstile verify result:", response)

        if not response.get("success"):
            print("❌ Turnstile失敗")
            return FAIL_HTML, 400

        # ここではDiscord処理を待たない
        try:
            requests.post(
                "http://127.0.0.1:10000/api/verify",
                json={"user_id": int(user_id)},
                timeout=3
            )
        except Exception as e:
            print("❌ API CALL ERROR:", e)

        return SUCCESS_HTML

    except Exception as e:
        print("❌ VERIFY PAGE ERROR:", e)
        return FAIL_HTML, 500

# Bot通知API
@app.route("/api/verify", methods=["POST"])
def verify_api():
    try:
        print("🔥 API HIT")

        data = request.get_json()
        if not data or "user_id" not in data:
            return {"error": "user_id missing"}, 400

        user_id = int(data["user_id"])
        print("user_id:", user_id)

        guild = client.get_guild(int(GUILD_ID))
        print("guild:", guild)

        if guild is None:
            return {"error": "guild not found"}, 500

        async def process():
            try:
                print("⏳ 1. member取得開始")

                member = guild.get_member(user_id)
                if member is None:
                    print("⏳ 2. get_memberで見つからないのでfetch_member")
                    member = await guild.fetch_member(user_id)
                else:
                    print("✅ 2. get_memberで取得成功")

                print("✅ 3. member:", member)

                remove_role = guild.get_role(VERIFY_ROLE_REMOVE)
                add_role = guild.get_role(VERIFY_ROLE_ADD)

                print("⏳ 4. remove role")
                if remove_role:
                    await member.remove_roles(remove_role)

                print("⏳ 5. add role")
                if add_role:
                    await member.add_roles(add_role)

                print("✅ 6. ロール処理完了")

            except Exception as e:
                print("❌ PROCESS ERROR:", e)

        client.loop.create_task(process())

        return {"status": "ok"}

    except Exception as e:
        print("❌ API ERROR:", e)
        return {"error": str(e)}, 500



def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)


threading.Thread(target=run_flask, daemon=True).start()


