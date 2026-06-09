import csv
import io
import os
from datetime import datetime, timezone
from secrets import token_urlsafe

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, func, select


def normalize_database_url(url: str) -> str:
    """Make Railway/Heroku-style postgres URLs work with SQLAlchemy + psycopg 3."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-railway")

raw_database_url = os.environ.get("DATABASE_URL", "sqlite:///petition.db")
database_url = normalize_database_url(raw_database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
metadata = MetaData()

signatures = Table(
    "signatures",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("rationale", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
)


def init_db() -> None:
    metadata.create_all(engine)


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_globals():
    return {"csrf_token": get_csrf_token}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        form_token = request.form.get("csrf_token", "")
        if not form_token or form_token != session.get("csrf_token"):
            flash("Security check failed. Please try again.", "error")
            return redirect(url_for("index"))

        name = " ".join(request.form.get("name", "").strip().split())
        rationale = request.form.get("rationale", "").strip()
        pledge = request.form.get("pledge") == "on"

        if not name:
            flash("Please enter your name before signing.", "error")
            return redirect(url_for("index"))
        if len(name) > 120:
            flash("Name is too long. Please keep it under 120 characters.", "error")
            return redirect(url_for("index"))
        if len(rationale) > 1000:
            flash("Rationale is too long. Please keep it under 1,000 characters.", "error")
            return redirect(url_for("index"))
        if not pledge:
            flash("Please confirm that you are signing with your own name.", "error")
            return redirect(url_for("index"))

        with engine.begin() as conn:
            conn.execute(
                signatures.insert().values(
                    name=name,
                    rationale=rationale or None,
                    created_at=datetime.now(timezone.utc),
                )
            )

        session["signed"] = True
        flash("Thank you. Your signature has been added.", "success")
        return redirect(url_for("index", signed="1"))

    with engine.connect() as conn:
        count = conn.execute(select(func.count()).select_from(signatures)).scalar_one()
        recent = conn.execute(
            select(signatures.c.name, signatures.c.rationale, signatures.c.created_at)
            .order_by(signatures.c.id.desc())
            .limit(10)
        ).mappings().all()

    return render_template("index.html", count=count, recent=recent, signed=session.get("signed", False))


@app.get("/signatures")
def signature_list():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 50
    offset = (page - 1) * per_page

    with engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(signatures)).scalar_one()
        rows = conn.execute(
            select(signatures.c.name, signatures.c.rationale, signatures.c.created_at)
            .order_by(signatures.c.id.desc())
            .limit(per_page)
            .offset(offset)
        ).mappings().all()

    has_next = offset + per_page < total
    return render_template(
        "signatures.html",
        rows=rows,
        total=total,
        page=page,
        has_next=has_next,
        has_prev=page > 1,
    )


@app.get("/export.csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "rationale", "signed_at_utc"])

    with engine.connect() as conn:
        rows = conn.execute(
            select(signatures.c.name, signatures.c.rationale, signatures.c.created_at).order_by(signatures.c.id.asc())
        ).all()

    for name, rationale, created_at in rows:
        writer.writerow([name, rationale or "", created_at.isoformat() if created_at else ""])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=midterm_petition_signatures.csv"},
    )


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
