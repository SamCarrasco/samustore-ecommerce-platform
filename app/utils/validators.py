import re, unicodedata
from app.models import User
from app import db

def slugify(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-zA-Z0-9\s-]', '', value).strip().lower()
    value = re.sub(r'[\s_-]+', '-', value)
    return value or 'tienda'

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def email_exists(email: str) -> bool:
    return db.session.query(User.query.filter_by(email=email).exists()).scalar()

def subdomain_exists(subdomain: str) -> bool:
    return db.session.query(User.query.filter_by(subdomain=subdomain).exists()).scalar()

def suggest_subdomains(base: str, k: int = 3):
    base = slugify(base)
    i = 2
    out = []
    while len(out) < k:
        cand = f"{base}-{i}"
        if not subdomain_exists(cand):
            out.append(cand)
        i += 1
    return out
