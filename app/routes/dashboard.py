# app/routes/dashboard.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.models import Product, User, SocialMedia
from app import db
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from decimal import Decimal, InvalidOperation
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
import re
from urllib.parse import quote_plus, urlparse, parse_qs, unquote_plus



bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')




# ---------- Helpers ----------
def _parse_decimal(value: str, field_name="precio"):
    if value is None or str(value).strip() == "":
        raise ValueError(f"El {field_name} es requerido.")
    try:
        d = Decimal(str(value))
        if d < 0:
            raise ValueError(f"El {field_name} no puede ser negativo.")
        return d
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name.capitalize()} inválido.")

def _parse_date(value: str):
    if not value:
        return None
    # acepta "YYYY-MM-DD"
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Fecha inválida (usa formato AAAA-MM-DD).")

def _own_product_or_404(pid: int):
    prod = Product.query.get_or_404(pid)
    if prod.user_id != current_user.id:
        abort(404)
    return prod

# ---------- Dashboard: listado ----------
@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    q = Product.query.filter_by(user_id=current_user.id)
    products = q.order_by(Product.created_at.desc()).paginate(page=page, per_page=per_page)
    total = q.count()
    disponibles = q.filter_by(status='available').count()

    return render_template(
        'dashboard/index.html',
        products=products,
        total=total,
        disponibles=disponibles
    )

# -------- Home ----------
@bp.route('/home')
@login_required
def home():
    return render_template('dashboard/home.html')


# Alias opcional si quieres /dashboard/products separado
@bp.route('/products')
@login_required
def products():
    return redirect(url_for('dashboard.index'))

# ---------- Crear producto ----------
@bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def product_new():
    if request.method == 'POST':
        # Lectura de campos del formulario
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form.get('price')
        original_raw = request.form.get('original_price')
        discount_start_raw = request.form.get('discount_start')
        discount_end_raw = request.form.get('discount_end')
        status = request.form.get('status', 'available')
        image_url_field = request.form.get('image_url', '').strip()
        file = request.files.get('image_file')

        try:
            # Validaciones básicas
            if not name:
                raise ValueError("El nombre es requerido.")

            price = _parse_decimal(price_raw, "precio")

            original_price = None
            if original_raw:
                original_price = _parse_decimal(original_raw, "precio original")

            discount_start = _parse_date(discount_start_raw)
            discount_end = _parse_date(discount_end_raw)
            if discount_start and discount_end and discount_end < discount_start:
                raise ValueError("La fecha fin de descuento no puede ser anterior al inicio.")

            # Imagen: archivo subido tiene prioridad sobre URL
            final_image_value = None
            if file and file.filename:
                if not _allowed_image(file.filename):
                    raise ValueError("Formato de imagen no permitido.")
                final_image_value = _save_image(file, current_user.id)  # ej: "uploads/42/uuid.jpg"
            elif image_url_field:
                final_image_value = image_url_field  # link externo

            p = Product(
                user_id=current_user.id,
                name=name,
                description=description or None,
                price=price,
                original_price=original_price,
                discount_start=discount_start,
                discount_end=discount_end,
                image_url=final_image_value,   # relativo o absoluto
                status=status if status in ('available', 'unavailable') else 'available'
            )
            db.session.add(p)
            db.session.commit()
            flash('Producto creado correctamente.', 'success')
            return redirect(url_for('dashboard.index'))

        except ValueError as e:
            flash(str(e), 'danger')

    # GET
    return render_template('dashboard/product_form.html', mode='create', product=None)



# ---------- Editar producto ----------
@bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(id):
    product = _own_product_or_404(id)

    if request.method == 'POST':
        # Lectura de campos del formulario
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form.get('price')
        original_raw = request.form.get('original_price')
        discount_start_raw = request.form.get('discount_start')
        discount_end_raw = request.form.get('discount_end')
        status = request.form.get('status', 'available')
        image_url_field = request.form.get('image_url', '').strip()
        file = request.files.get('image_file')

        try:
            # Validaciones básicas
            if not name:
                raise ValueError("El nombre es requerido.")

            price = _parse_decimal(price_raw, "precio")

            original_price = None
            if original_raw:
                original_price = _parse_decimal(original_raw, "precio original")

            discount_start = _parse_date(discount_start_raw)
            discount_end = _parse_date(discount_end_raw)
            if discount_start and discount_end and discount_end < discount_start:
                raise ValueError("La fecha fin de descuento no puede ser anterior al inicio.")

            # Imagen:
            if file and file.filename:
                if not _allowed_image(file.filename):
                    raise ValueError("Formato de imagen no permitido.")
                # Borrar archivo anterior si era local
                if product.image_url and not product.image_url.startswith("http"):
                    old_abs = os.path.join("app/static", product.image_url)
                    if os.path.exists(old_abs):
                        try:
                            os.remove(old_abs)
                        except OSError:
                            pass
                product.image_url = _save_image(file, current_user.id)
            else:
                # Si no se sube nueva, permitir reemplazo por URL (opcional)
                if image_url_field:
                    product.image_url = image_url_field

            # Asignar campos restantes
            product.name = name
            product.description = description or None
            product.price = price
            product.original_price = original_price
            product.discount_start = discount_start
            product.discount_end = discount_end
            product.status = status if status in ('available', 'unavailable') else 'available'

            db.session.commit()
            flash('Producto actualizado.', 'success')
            return redirect(url_for('dashboard.index'))

        except ValueError as e:
            flash(str(e), 'danger')

    # GET
    return render_template('dashboard/product_form.html', mode='edit', product=product)


# ---------- Eliminar producto ----------
@bp.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def product_delete(id):
    product = _own_product_or_404(id)

    # Borrar imagen local si existe y no es URL externa
    if product.image_url and not product.image_url.startswith("http"):
        old_abs = os.path.join("app/static", product.image_url)
        if os.path.exists(old_abs):
            try:
                os.remove(old_abs)
            except OSError:
                pass

    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado.', 'info')
    return redirect(url_for('dashboard.index'))


# ---------- Perfil de la tienda / usuario ----------
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user: User = current_user  # type: ignore

    if request.method == 'POST':
        user.username = request.form.get('username', user.username).strip() or user.username
        user.userlastname = request.form.get('userlastname', user.userlastname).strip() or user.userlastname
        user.store_name = request.form.get('store_name', user.store_name).strip() or user.store_name
        user.store_address = request.form.get('store_address', user.store_address).strip() or user.store_address
        user.celphone = request.form.get('celphone', user.celphone).strip() or user.celphone
        user.country = request.form.get('country', user.country).strip() or user.country
        user.city = request.form.get('city', user.city).strip() or user.city

        try:
            db.session.commit()
            flash('Perfil actualizado.', 'success')
            return redirect(url_for('dashboard.profile'))
        except IntegrityError:
            db.session.rollback()
            flash('El email ya está en uso.', 'danger')

    # GET
    return render_template('dashboard/profile.html', user=user)




# -------- Manejo de imágenes -----------
# imagenes permitidas
def _allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
# guardar imagen

def _save_image(file_storage, user_id: int) -> str:
    base_folder = current_app.config.get("UPLOAD_FOLDER", "app/static/uploads")
    user_folder = os.path.join(base_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    unique = f"{uuid.uuid4().hex}.{ext}"

    abs_path = os.path.join(user_folder, unique)
    file_storage.save(abs_path)

    rel_from_static = os.path.relpath(abs_path, start="app/static")

    # 🔧 Fix aquí: convertir `\` en `/` para rutas web
    rel_from_static = rel_from_static.replace("\\", "/")

    return rel_from_static




# ------------------- helpers sociales nuevos -------------------
_PLATFORMS = ("facebook", "instagram", "twitter", "tiktok", "whatsapp")

def _clean_handle(s: str) -> str | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    if s.startswith('@'):
        s = s[1:]
    # remove trailing slashes
    s = s.strip('/')
    return s or None

def _ensure_url(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not re.match(r'^https?://', url, flags=re.I):
        url = 'https://' + url
    return url

def _build_url_from_handle(platform: str, handle_or_url: str) -> str | None:
    """
    Si empieza con http, se toma como URL y se normaliza.
    Si es handle, se genera la URL canónica por plataforma.
    """
    if not handle_or_url:
        return None
    hv = handle_or_url.strip()
    if not hv:
        return None

    if re.match(r'^https?://', hv, re.I):
        return _ensure_url(hv)

    handle = _clean_handle(hv)
    if not handle:
        return None

    if platform == "instagram":
        return f"https://instagram.com/{handle}"
    if platform == "twitter":
        return f"https://twitter.com/{handle}"
    if platform == "tiktok":
        # TikTok suele usar @ en la URL
        return f"https://tiktok.com/@{handle}"
    if platform == "facebook":
        # Para Facebook preferimos URL completa; si pasas solo handle, asumimos página
        return f"https://facebook.com/{handle}"
    return None

def _build_whatsapp_url(number_raw: str, message_raw: str | None) -> str | None:
    if not number_raw:
        return None
    digits = re.sub(r'\D+', '', number_raw)
    if not digits:
        return None
    url = f"https://wa.me/{digits}"
    if message_raw:
        msg = message_raw.strip()
        if msg:
            url += f"?text={quote_plus(msg)}"
    return url

def _upsert_social(user_id: int, platform: str, url: str | None):
    """
    Crea/actualiza o elimina el registro de SocialMedia para (user, platform).
    """
    if platform not in _PLATFORMS:
        return
    row = SocialMedia.query.filter_by(user_id=user_id, platform=platform).first()
    if url:
        if row:
            row.url = url
        else:
            db.session.add(SocialMedia(user_id=user_id, platform=platform, url=url))
    else:
        if row:
            db.session.delete(row)

def _extract_handle_from_url(platform: str, url: str) -> str | None:
    try:
        p = urlparse(url)
        path = p.path.strip('/')
        if platform == "tiktok":
            # /@handle[/...]
            m = re.match(r'^@([^/]+)', path)
            return m.group(1) if m else None
        else:
            # instagram/twitter/facebook: first segment is handle/page
            segs = path.split('/')
            return segs[0] if segs and segs[0] else None
    except Exception:
        return None

def _extract_whatsapp_parts(url: str) -> tuple[str | None, str | None]:
    """
    Devuelve (numero, mensaje) desde una URL wa.me si es posible.
    """
    try:
        p = urlparse(url)
        m = re.search(r'/(\d+)', p.path)
        number = m.group(1) if m else None
        q = parse_qs(p.query or "")
        message = unquote_plus(q.get('text', [''])[0]) if 'text' in q else None
        return number, (message or None)
    except Exception:
        return None, None


# ------------------- Social -------------------
@bp.route('/social', methods=['GET', 'POST'])
@login_required
def social():
    user: User = current_user  # type: ignore

    if request.method == 'POST':
        # Instagram/Twitter/TikTok/Facebook: permitimos handle o URL
        ig_input = request.form.get('instagram', '')
        tw_input = request.form.get('twitter', '')
        tk_input = request.form.get('tiktok', '')
        fb_input = request.form.get('facebook', '')

        ig_url = _build_url_from_handle("instagram", ig_input)
        tw_url = _build_url_from_handle("twitter",   tw_input)
        tk_url = _build_url_from_handle("tiktok",    tk_input)
        fb_url = _build_url_from_handle("facebook",  fb_input)

        # WhatsApp: número y mensaje
        wa_number = request.form.get('whatsapp_number', '')
        wa_message = request.form.get('whatsapp_message', '')
        wa_url = _build_whatsapp_url(wa_number, wa_message)

        # Upsert atómico por plataforma
        try:
            _upsert_social(user.id, "instagram", ig_url)
            _upsert_social(user.id, "twitter",   tw_url)
            _upsert_social(user.id, "tiktok",    tk_url)
            _upsert_social(user.id, "facebook",  fb_url)
            _upsert_social(user.id, "whatsapp",  wa_url)
            db.session.commit()
            flash('Enlaces sociales actualizados.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error de base de datos al guardar redes sociales.', 'danger')

        return redirect(url_for('dashboard.social'))

    # GET: obtenemos las URLs guardadas para prefill y preview
    rows = SocialMedia.query.filter_by(user_id=user.id).all()
    social_map = {r.platform: r.url for r in rows}

    # Prefill de campos “handle” para IG/Twitter/TikTok si es posible
    ig_prefill = _extract_handle_from_url("instagram", social_map.get("instagram", "")) if social_map.get("instagram") else ""
    tw_prefill = _extract_handle_from_url("twitter",   social_map.get("twitter", "")) if social_map.get("twitter") else ""
    tk_prefill = _extract_handle_from_url("tiktok",    social_map.get("tiktok", "")) if social_map.get("tiktok") else ""

    # Facebook preferimos mostrar URL completa
    fb_prefill = social_map.get("facebook", "") or ""

    # WhatsApp: extraemos número y mensaje si la URL existe
    wa_number_prefill = ""
    wa_message_prefill = ""
    if social_map.get("whatsapp"):
        n, m = _extract_whatsapp_parts(social_map["whatsapp"])
        wa_number_prefill = n or ""
        wa_message_prefill = m or ""

    # Enlaces de vista previa (son las mismas URLs guardadas)
    links = {
        "Instagram": social_map.get("instagram"),
        "Twitter":   social_map.get("twitter"),
        "TikTok":    social_map.get("tiktok"),
        "Facebook":  social_map.get("facebook"),
        "WhatsApp":  social_map.get("whatsapp"),
    }

    return render_template(
        'dashboard/social.html',
        user=user,
        prefill={
            "instagram": ig_prefill,
            "twitter":   tw_prefill,
            "tiktok":    tk_prefill,
            "facebook":  fb_prefill,
            "wa_number": wa_number_prefill,
            "wa_message": wa_message_prefill,
        },
        links=links
    )