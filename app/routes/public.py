from flask import Blueprint, render_template, request
from app.models import User, Product
from sqlalchemy import or_

bp = Blueprint("public", __name__, url_prefix="/public")

@bp.route("/<subdomain>")
def store_catalog(subdomain):
    user = User.query.filter_by(subdomain=subdomain).first_or_404(description="Tienda no encontrada")

    # Parámetros
    page     = max(1, request.args.get("page", 1, type=int))
    per_page = min(24, max(1, request.args.get("per_page", 12, type=int)))
    qtext    = (request.args.get("q", "") or "").strip()
    sort     = request.args.get("sort", "new")  # new | price_asc | price_desc

    # Query base
    q = Product.query.filter(
        Product.user_id == user.id,
        Product.status == "available"
    )

    if qtext:
        like = f"%{qtext}%"
        q = q.filter(or_(Product.name.ilike(like), Product.description.ilike(like)))

    # Orden
    if sort == "price_asc":
        q = q.order_by(Product.price.asc(), Product.created_at.desc())
    elif sort == "price_desc":
        q = q.order_by(Product.price.desc(), Product.created_at.desc())
    else:
        q = q.order_by(Product.created_at.desc())

    total = q.count()
    products = q.paginate(page=page, per_page=per_page)

    # Redes sociales del comercio (dict por plataforma)
    links = { sm.platform: sm.url for sm in user.socialmedia }

    return render_template(
        "public/store.html",
        store_owner=user,
        store_name=user.store_name,
        store_slug=user.subdomain,     # para construir URLs
        products=products,
        total=total,
        q=qtext,
        sort=sort,
        per_page=per_page,
        links=links,
    )
