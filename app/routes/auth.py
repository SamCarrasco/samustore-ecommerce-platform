from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.forms import LoginForm, RegisterForm
from app.models import User
from app import db, slugify  # usamos tu slugify del __init__.py
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

bp = Blueprint('auth', __name__, url_prefix='/auth')


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def email_exists(email: str) -> bool:
    return db.session.query(User.query.filter_by(email=email).exists()).scalar()


def subdomain_exists(subdomain: str) -> bool:
    return db.session.query(User.query.filter_by(subdomain=subdomain).exists()).scalar()


def suggest_subdomains(base: str, k: int = 3):
    """Devuelve k sugerencias disponibles a partir del slug base."""
    base = slugify(base) or "tienda"
    out = []
    i = 2
    while len(out) < k:
        candidate = f"{base}-{i}"
        if not subdomain_exists(candidate):
            out.append(candidate)
        i += 1
    return out


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = normalize_email(form.email.data)
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data if hasattr(form, "remember") else False)
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('dashboard.home'))
        else:
            flash('Credenciales inválidas.', 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    suggested = []

    if form.validate_on_submit():
        # Normalizaciones
        email = normalize_email(form.email.data)
        # Si no envía subdomain, usamos store_name como base
        raw_sub = (form.subdomain.data or form.store_name.data or "").strip()
        subdomain = slugify(raw_sub)

        # Validaciones de unicidad (app-level)
        has_error = False
        if email_exists(email):
            form.email.errors.append('Este email ya está registrado.')
            has_error = True

        if subdomain_exists(subdomain):
            suggested = suggest_subdomains(subdomain, k=3)
            form.subdomain.errors.append(
                f'El subdominio “{subdomain}” ya está en uso. Prueba: {", ".join(suggested)}'
            )
            has_error = True

        if has_error:
            # Render con errores de WTForms + sugerencias
            return render_template('auth/register.html', form=form, suggested=suggested)

        # Crear usuario
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data.strip(),
            userlastname=form.userlastname.data.strip(),
            email=email,
            password=hashed_password,
            store_name=form.store_name.data.strip(),
            store_address=form.store_address.data.strip(),
            celphone=form.celphone.data.strip(),
            subdomain=subdomain,  # único
            country=form.country.data.strip(),
            city=form.city.data.strip(),
            status='active'
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Cuenta creada con éxito. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))
        except IntegrityError as e:
            db.session.rollback()
            # Defensa ante condiciones de carrera: detectamos qué campo chocó
            err = str(getattr(e.orig, 'args', e.args))
            # Ajusta los contains según tu backend (MySQL/MariaDB suele traer "for key '...index...'")
            if 'usuarios.email' in err or "for key 'usuarios.email'" in err:
                form.email.errors.append('Este email ya está registrado.')
            elif 'usuarios.subdomain' in err or "for key 'usuarios.subdomain'" in err:
                suggested = suggest_subdomains(subdomain, k=3)
                form.subdomain.errors.append(
                    f'El subdominio “{subdomain}” ya está en uso. Prueba: {", ".join(suggested)}'
                )
            else:
                flash('No pudimos crear la cuenta por un error de base de datos. Intenta nuevamente.', 'danger')
                # También podrías loguear el error en tu logger
            return render_template('auth/register.html', form=form, suggested=suggested)

    # GET o POST inválido
    return render_template('auth/register.html', form=form, suggested=suggested)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    # Limpia pendientes y comunica estado
    from flask import get_flashed_messages
    get_flashed_messages()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))
