from flask import Flask, request, jsonify, redirect, abort, render_template
import os, secrets, string

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import psycopg

    def get_conn():
        return psycopg.connect(DATABASE_URL, connect_timeout=10)

    def norm(sql):
        return sql
else:
    import sqlite3

    def get_conn():
        return sqlite3.connect("urls.db")

    def norm(sql):
        return sql.replace("%s", "?")


def run(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.execute(norm(sql), params)
        conn.commit()
        if cur.description is not None:
            return cur.fetchall()
    finally:
        conn.close()


run("CREATE TABLE IF NOT EXISTS links (code TEXT UNIQUE, url TEXT)")


def generate_code():
    code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    return code


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True) or {}
    req_url = (data.get("url") or "").strip()
    if not req_url:
        return jsonify({"error": "Server received no URL!"}), 400
    if not req_url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL prefix!"}), 400
    if len(req_url) > 2048:
        return jsonify({"error": "URL too long!"}), 400
    for _ in range(5):
        code = generate_code()
        try:
            run("INSERT INTO links (code, url) VALUES (%s, %s)", (code, req_url))
            break
        except Exception:
            continue
    else:
        return jsonify({"error": "Couldn't generate a code, try again!"}), 409
    return jsonify({"short": f"{request.host_url}{code}"}), 201


@app.route("/<code>")
def go(code):
    rows = run("SELECT url FROM links WHERE code = %s", (code,))
    if not rows:
        abort(404)
    return redirect(rows[0][0])


if __name__ == "__main__":
    app.run(port=3000)