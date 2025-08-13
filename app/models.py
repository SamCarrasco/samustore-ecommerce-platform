from app import db
from flask_login import UserMixin


# === USUARIO ===
class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    userlastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    store_name = db.Column(db.String(100), nullable=False)
    store_address = db.Column(db.String(255), nullable=False)
    celphone = db.Column(db.String(20), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum('active', 'inactive'), default='active')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Relaciones
    products = db.relationship('Product', backref='owner', cascade='all, delete-orphan')
    socialmedia = db.relationship('SocialMedia', backref='user', cascade='all, delete-orphan')
    logs = db.relationship('Log', backref='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'

    def get_id(self):
        return str(self.id)  # Necesario para Flask-Login


# === PRODUCTOS ===
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    original_price = db.Column(db.Numeric(10, 2), default=None)
    discount_start = db.Column(db.Date, default=None)
    discount_end = db.Column(db.Date, default=None)
    image_url = db.Column(db.String(255))
    status = db.Column(db.Enum('available', 'unavailable'), default='available')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<Product {self.name}>'


# === REDES SOCIALES ===
class SocialMedia(db.Model):
    __tablename__ = 'socialmedia'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'platform', name='uq_socialmedia_user_platform'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    platform = db.Column(db.Enum('facebook', 'instagram', 'twitter', 'tiktok', 'whatsapp', 'telegram',
                                 'youtube', 'website'),
                         nullable=False)
    url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<SocialMedia {self.platform}>'


# === LOG DE ACCIONES ===
class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    entity_type = db.Column(db.Enum('product', 'user', 'login', 'store'), nullable=False)
    entity_id = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<Log {self.action} - {self.entity_type}>'
