from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember = BooleanField('Recordarme')
    submit = SubmitField('Iniciar sesión')


class RegisterForm(FlaskForm):
    username = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=50)])
    userlastname = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6, max=35)])
    confirm_password = PasswordField('Confirmar contraseña', validators=[DataRequired(), EqualTo('password')])
    store_name = StringField('Nombre de tienda', validators=[DataRequired()])
    store_address = StringField('Dirección', validators=[DataRequired()])
    celphone = StringField('Celular', validators=[DataRequired()])
    subdomain = StringField('Subdominio', validators=[DataRequired()])
    country = StringField('País', validators=[DataRequired()])
    city = StringField('Ciudad', validators=[DataRequired()])
    submit = SubmitField('Crear cuenta')
