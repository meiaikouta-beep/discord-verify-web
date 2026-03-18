from flask import Flask, request, render_template_string
import requests

app = Flask(__name__)

SITE_KEY = "ここにsite key"
SECRET_KEY = "ここにsecret key"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
</head>
<body>
    <h2>認証してください</h2>
    <form method="POST">
        <div class="cf-turnstile" data-sitekey="{{ site_key }}"></div>
        <br>
        <button type="submit">認証</button>
    </form>
</body>
</html>
"""

@app.route("/")
def home():
    return "Flask is running!"

@app.route("/verify", methods=["GET", "POST"])
def verify():
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
            return "認証成功！"
        else:
            return "認証失敗"

    return render_template_string(HTML, site_key=SITE_KEY)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
