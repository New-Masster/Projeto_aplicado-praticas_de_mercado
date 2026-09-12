import os
import secrets
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash


app = Flask(__name__)


# ============================================================
# A04:2025 - Cryptographic Failures
# ============================================================
# Segredos obrigatórios fornecidos exclusivamente pelo ambiente.
# Não existem credenciais ou chaves hardcoded no código.

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FALHA DE SEGURANÇA: SECRET_KEY não configurada."
    )

if not ADMIN_PASSWORD_HASH:
    raise RuntimeError(
        "FALHA DE SEGURANÇA: ADMIN_PASSWORD_HASH não configurado."
    )


# ============================================================
# A02:2025 - Security Misconfiguration
# ============================================================
# Proteções da sessão.
#
# HttpOnly:
# impede acesso ao cookie de sessão via JavaScript.
#
# SameSite=Lax:
# reduz o envio automático da sessão em requisições
# cross-site.
#
# Secure:
# em produção será ativado somente quando HTTPS estiver
# sendo utilizado.
#
# No teste local usamos FLASK_SECURE_COOKIE=0.

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.environ.get(
        "FLASK_SECURE_COOKIE", "0"
    ) == "1",
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_NAME="session_sec",
)


# ============================================================
# A01:2025 - Broken Access Control
# ============================================================
# Todas as rotas que exigem autenticação devem utilizar
# este decorator.

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# A02:2025 - Security Misconfiguration
# ============================================================
# Headers defensivos adicionados globalmente às respostas.

@app.after_request
def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline';"
    )

    return response


# ============================================================
# Rotas públicas
# ============================================================

@app.route("/", methods=["GET"])
def index():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        username_valid = secrets.compare_digest(
            username,
            ADMIN_USERNAME
        )

        password_valid = check_password_hash(
            ADMIN_PASSWORD_HASH,
            password
        )

        if username_valid and password_valid:
            session.clear()
            session["authenticated"] = True
            session["username"] = username

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Usuário ou senha inválidos."
        ), 401

    return render_template("login.html")


# ============================================================
# Área protegida
# ============================================================

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        username=session.get("username")
    )


# ============================================================
# Logout
# ============================================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()

    return redirect(url_for("login"))


# ============================================================
# Execução local
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000
    )