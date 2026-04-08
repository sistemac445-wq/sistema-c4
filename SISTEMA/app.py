import os
import logging
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

# --- LOGS ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- APP ---
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- BASE DE DATOS ---
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info("Conectado a la base de datos remota.")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/railway'
    logger.warning("Conectado a localhost (DB: railway).")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_segura_tickets')

# --- COOKIES (UN SOLO BLOQUE, SIN DUPLICADOS) ---
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

db = SQLAlchemy(app)

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None

# --- UPLOADS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ROLES_DISPONIBLES = ['Admin', 'Tecnico', 'Usuario']

# ---------------------- MODELOS ----------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    sector = db.Column(db.String(50))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class EquipoReporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    responsable_nombre = db.Column(db.String(100), nullable=False)
    responsable_sector = db.Column(db.String(100))
    telefono_responsable = db.Column(db.String(30))
    sector = db.Column(db.String(50))
    inventario_numero = db.Column(db.String(50))
    falla_descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), default='Pendiente')
    fecha_reporte = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fecha_reparacion = db.Column(db.DateTime, nullable=True)
    foto_reparado_path = db.Column(db.String(255), nullable=True)
    user = db.relationship('User', backref=db.backref('equipo_reportes', lazy=True))

class PatrullaReporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    unidad_numero = db.Column(db.String(50), nullable=False)
    sector = db.Column(db.String(50))
    oficial_nombre = db.Column(db.String(100))
    placa = db.Column(db.String(30))
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    turno = db.Column(db.String(30))
    fecha_reporte = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fecha_reparacion = db.Column(db.DateTime, nullable=True)
    falla_descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default='Pendiente')
    observaciones = db.Column(db.Text)
    foto_falla_path = db.Column(db.String(255), nullable=True)
    foto_reparado_path = db.Column(db.String(255), nullable=True)
    camara1_funciona = db.Column(db.Boolean, default=True)
    camara2_funciona = db.Column(db.Boolean, default=True)
    camara3_funciona = db.Column(db.Boolean, default=True)
    camara4_funciona = db.Column(db.Boolean, default=True)
    grabadora1_funciona = db.Column(db.Boolean, default=True)
    grabadora2_funciona = db.Column(db.Boolean, default=True)
    grabadora3_funciona = db.Column(db.Boolean, default=True)
    grabadora4_funciona = db.Column(db.Boolean, default=True)
    falla_camara_desc_1 = db.Column(db.Text)
    falla_camara_desc_2 = db.Column(db.Text)
    falla_camara_desc_3 = db.Column(db.Text)
    falla_camara_desc_4 = db.Column(db.Text)
    falla_camara_foto_1 = db.Column(db.String(255))
    falla_camara_foto_2 = db.Column(db.String(255))
    falla_camara_foto_3 = db.Column(db.String(255))
    falla_camara_foto_4 = db.Column(db.String(255))
    falla_grabadora_desc_1 = db.Column(db.Text)
    falla_grabadora_desc_2 = db.Column(db.Text)
    falla_grabadora_desc_3 = db.Column(db.Text)
    falla_grabadora_desc_4 = db.Column(db.Text)
    falla_grabadora_foto_1 = db.Column(db.String(255))
    falla_grabadora_foto_2 = db.Column(db.String(255))
    falla_grabadora_foto_3 = db.Column(db.String(255))
    falla_grabadora_foto_4 = db.Column(db.String(255))
    user = db.relationship('User', backref=db.backref('patrulla_reportes', lazy=True))

def guardar_foto(foto):
    if foto and foto.filename != '':
        try:
            filename = secure_filename(foto.filename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(path)
            return path
        except Exception as e:
            app.logger.error(f"Error al guardar foto: {e}")
    return None

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}

# ---------------------- RUTAS ----------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Credenciales inválidas', 'danger')
        except Exception as e:
            logger.error(f"Error de BD: {e}")
            flash('Error de conexión con la base de datos.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'Tecnico':
        return redirect(url_for('tecnico_dashboard'))
    elif current_user.role == 'Usuario':
        return redirect(url_for('oficial_dashboard'))
    else:
        logout_user()
        flash(f'Rol "{current_user.role}" no reconocido. Contacta al administrador.', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        logout_user()
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for('login'))

# ---------------------- ADMIN USUARIOS ----------------------

@app.route('/admin/usuarios', methods=['GET', 'POST'])
@login_required
def admin_usuarios():
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        sector = request.form.get('sector', '').strip()

        if not username or not password or not role:
            flash('Usuario, contraseña y rol son obligatorios.', 'danger')
            usuarios = User.query.order_by(User.username).all()
            return render_template('admin_usuarios.html', user=current_user, usuarios=usuarios, roles=ROLES_DISPONIBLES)

        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe.', 'danger')
            usuarios = User.query.order_by(User.username).all()
            return render_template('admin_usuarios.html', user=current_user, usuarios=usuarios, roles=ROLES_DISPONIBLES)

        try:
            nuevo_usuario = User(username=username, role=role, sector=sector if sector else None)
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash(f'Usuario "{username}" creado exitosamente.', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el usuario.', 'danger')
            app.logger.error(f"Error al crear usuario: {e}")

    usuarios = User.query.order_by(User.username).all()
    return render_template('admin_usuarios.html', user=current_user, usuarios=usuarios, roles=ROLES_DISPONIBLES)


@app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_editar_usuario(user_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))

    usuario = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip()
        sector = request.form.get('sector', '').strip()
        nueva_password = request.form.get('password', '').strip()

        if not username or not role:
            flash('Usuario y rol son obligatorios.', 'danger')
            return render_template('admin_editar_usuario.html', user=current_user, usuario=usuario, roles=ROLES_DISPONIBLES)

        existente = User.query.filter_by(username=username).first()
        if existente and existente.id != user_id:
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('admin_editar_usuario.html', user=current_user, usuario=usuario, roles=ROLES_DISPONIBLES)

        try:
            usuario.username = username
            usuario.role = role
            usuario.sector = sector if sector else None
            if nueva_password:
                usuario.set_password(nueva_password)
            db.session.commit()
            flash(f'Usuario "{username}" actualizado exitosamente.', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el usuario.', 'danger')
            app.logger.error(f"Error al editar usuario: {e}")

    return render_template('admin_editar_usuario.html', user=current_user, usuario=usuario, roles=ROLES_DISPONIBLES)


@app.route('/admin/usuarios/eliminar/<int:user_id>', methods=['POST'])
@login_required
def admin_eliminar_usuario(user_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))

    if user_id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('admin_usuarios'))

    usuario = User.query.get_or_404(user_id)
    try:
        db.session.delete(usuario)
        db.session.commit()
        flash(f'Usuario "{usuario.username}" eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el usuario.', 'danger')
        app.logger.error(f"Error al eliminar usuario: {e}")

    return redirect(url_for('admin_usuarios'))


# ---------------------- DASHBOARDS ----------------------

@app.route('/oficial/dashboard')
@login_required
def oficial_dashboard():
    # Si no es Usuario, redirigir a la función central, no al login
    if current_user.role != 'Usuario':
        return redirect(url_for('dashboard')) 
    return render_template('usuario_dashboard.html', user=current_user)

@app.route('/tecnico/dashboard')
@login_required
def tecnico_dashboard():
    # Si no es Tecnico, redirigir a la función central
    if current_user.role != 'Tecnico':
        return redirect(url_for('dashboard'))
    base_query_equipo = EquipoReporte.query.filter(
        EquipoReporte.estado.in_(['Pendiente', 'En Progreso'])
    )
    base_query_patrulla = PatrullaReporte.query.filter(
        PatrullaReporte.estado.in_(['Pendiente', 'En Progreso'])
    )

    if current_user.sector and current_user.sector != 'Global':
        base_query_equipo = base_query_equipo.filter_by(sector=current_user.sector)
        base_query_patrulla = base_query_patrulla.filter_by(sector=current_user.sector)

    pendientes_equipo = base_query_equipo.order_by(EquipoReporte.fecha_reporte.asc()).all()
    pendientes_patrulla = base_query_patrulla.order_by(PatrullaReporte.fecha_reporte.asc()).all()

    return render_template('tecnico_dashboard.html',
                           user=current_user,
                           pendientes_equipo=pendientes_equipo,
                           pendientes_patrulla=pendientes_patrulla)


# ---------------------- REPORTES ----------------------

@app.route('/reporte_equipo', methods=['GET', 'POST'])
@login_required
def reporte_equipo_form():
    if request.method == 'POST':
        resp_nom = request.form.get('responsable_nombre')
        resp_sec = request.form.get('responsable_sector')
        resp_tel = request.form.get('telefono_responsable')
        tipo_equipo = request.form.get('tipo')
        num_serie = request.form.get('serie')
        est_operativo = request.form.get('estado_operativo')
        comentarios = request.form.get('comentarios')

        if not all([resp_nom, resp_sec, resp_tel, tipo_equipo, num_serie, est_operativo, comentarios]):
            flash("Error: Todos los campos marcados con (*) son obligatorios.", "danger")
            return render_template('reporte_equipo_form.html')

        try:
            nuevo_reporte = EquipoReporte(
                user_id=current_user.id,
                responsable_nombre=resp_nom,
                responsable_sector=resp_sec,
                telefono_responsable=resp_tel,
                sector=current_user.sector or 'Sin Sector',
                inventario_numero=num_serie,
                falla_descripcion=f"[{tipo_equipo}] - Estado: {est_operativo}\n\n{comentarios}",
                estado='Pendiente',
                fecha_reporte=datetime.datetime.now(datetime.timezone.utc)
            )
            db.session.add(nuevo_reporte)
            db.session.commit()
            flash("✓ El reporte se ha guardado exitosamente.", "success")
            return redirect(url_for('oficial_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"DEBUG ERROR: {e}")
            flash(f"Error al guardar en la base de datos: {str(e)}", "danger")

    return render_template('reporte_equipo_form.html')


@app.route('/reporte/patrulla', methods=['GET', 'POST'])
@login_required
def reporte_patrulla_form():
    if current_user.role not in ['Tecnico', 'Admin']:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            unidad_numero = request.form.get('unidad_numero', '').strip()
            oficial_nombre = request.form.get('oficial_nombre', '').strip()
            placa = request.form.get('placa', '').strip()
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            turno = request.form.get('turno', '').strip()
            sector_unidad = request.form.get('sector', '').strip()
            fecha_reporte_str = request.form.get('fecha_reporte')

            if not all([unidad_numero, oficial_nombre, placa, marca, modelo, turno, sector_unidad]):
                flash('Faltan campos obligatorios.', 'danger')
                return render_template('reporte_patrulla_form.html', user=current_user)

            try:
                fecha_reporte = datetime.datetime.fromisoformat(fecha_reporte_str)
            except (ValueError, TypeError):
                fecha_reporte = datetime.datetime.now()

            todas_ok = True
            falla_lista = []
            componentes_status = {}
            componentes_detalle = {}
            primera_foto_global = None

            for i in range(1, 5):
                cam_funciona = request.form.get(f'camara_{i}') == '1'
                componentes_status[f'camara{i}_funciona'] = cam_funciona
                if not cam_funciona:
                    todas_ok = False
                    detalle = request.form.get(f'falla_camara_desc_{i}', '').strip()
                    foto = request.files.get(f'falla_camara_foto_{i}')
                    falla_lista.append(f"[Cámara {i}]: {detalle}")
                    componentes_detalle[f'falla_camara_desc_{i}'] = detalle
                    path_foto = guardar_foto(foto)
                    componentes_detalle[f'falla_camara_foto_{i}'] = path_foto
                    if path_foto and not primera_foto_global:
                        primera_foto_global = path_foto

                grab_funciona = request.form.get(f'grabadora_{i}') == '1'
                componentes_status[f'grabadora{i}_funciona'] = grab_funciona
                if not grab_funciona:
                    todas_ok = False
                    detalle = request.form.get(f'falla_grabadora_desc_{i}', '').strip()
                    foto = request.files.get(f'falla_grabadora_foto_{i}')
                    falla_lista.append(f"[Grabadora {i}]: {detalle}")
                    componentes_detalle[f'falla_grabadora_desc_{i}'] = detalle
                    path_foto = guardar_foto(foto)
                    componentes_detalle[f'falla_grabadora_foto_{i}'] = path_foto
                    if path_foto and not primera_foto_global:
                        primera_foto_global = path_foto

            observaciones = request.form.get('observaciones', '').strip()
            if observaciones:
                falla_lista.append(f"[Obs. Técnico]: {observaciones}")

            falla_final = '\n'.join(falla_lista)
            estado = "Pendiente" if not todas_ok else "Cerrado"

            nuevo_reporte = PatrullaReporte(
                user_id=current_user.id,
                unidad_numero=unidad_numero,
                sector=sector_unidad,
                oficial_nombre=oficial_nombre,
                placa=placa,
                marca=marca,
                modelo=modelo,
                turno=turno,
                fecha_reporte=fecha_reporte,
                **componentes_status,
                **componentes_detalle,
                observaciones=observaciones,
                falla_descripcion=falla_final if falla_final else "Inspección sin novedades",
                estado=estado,
                foto_falla_path=primera_foto_global
            )

            if estado == 'Cerrado':
                nuevo_reporte.fecha_reparacion = datetime.datetime.now()

            db.session.add(nuevo_reporte)
            db.session.commit()
            flash(f"Inspección de unidad {unidad_numero} guardada correctamente.", "success")
            return redirect(url_for('tecnico_dashboard'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error en reporte técnico: {e}")
            flash("Error al procesar la inspección.", "danger")
            return render_template('reporte_patrulla_form.html', user=current_user)

    return render_template('reporte_patrulla_form.html', user=current_user)


@app.route('/mis_reportes')
@login_required
def mis_reportes():
    if current_user.role != 'Usuario':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    equipos = EquipoReporte.query.filter_by(user_id=current_user.id).order_by(EquipoReporte.fecha_reporte.desc()).all()
    patrullas = PatrullaReporte.query.filter_by(user_id=current_user.id).order_by(PatrullaReporte.fecha_reporte.desc()).all()
    return render_template('mis_reportes.html', user=current_user, equipos=equipos, patrullas=patrullas)


# ---------------------- EDITAR REPORTES ----------------------

@app.route('/reporte/equipo/editar/<int:reporte_id>', methods=['GET', 'POST'])
@login_required
def editar_reporte_equipo(reporte_id):
    if current_user.role not in ['Admin', 'Tecnico']:
        return redirect(url_for('login'))

    reporte = EquipoReporte.query.get_or_404(reporte_id)

    if request.method == 'POST':
        try:
            nuevo_estado = request.form.get('estado')
            if nuevo_estado:
                reporte.estado = nuevo_estado
                if nuevo_estado in ['Reparado', 'Cerrado']:
                    reporte.fecha_reparacion = datetime.datetime.utcnow()
                else:
                    reporte.fecha_reparacion = None

            foto_rep = request.files.get('foto_reparado')
            if foto_rep and foto_rep.filename != '':
                path_foto = guardar_foto(foto_rep)
                if path_foto:
                    reporte.foto_reparado_path = path_foto

            db.session.commit()
            flash(f"✅ Reporte #{reporte_id} actualizado con éxito.", "success")
            return redirect(url_for('admin_dashboard') if current_user.role == 'Admin' else url_for('tecnico_dashboard'))

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al editar equipo ID {reporte_id}: {e}")
            flash("❌ Error al guardar los cambios.", "danger")
            return redirect(url_for('tecnico_dashboard'))

    return render_template('editar_reporte_equipo.html', reporte=reporte)


@app.route('/reporte/patrulla/editar/<int:reporte_id>', methods=['GET', 'POST'])
@login_required
def editar_reporte_patrulla(reporte_id):
    if current_user.role not in ['Admin', 'Tecnico']:
        return redirect(url_for('login'))

    reporte = PatrullaReporte.query.get_or_404(reporte_id)

    if current_user.role == 'Tecnico' and current_user.sector != 'Global' and reporte.sector != current_user.sector:
        flash("No tienes permiso para gestionar reportes fuera de tu sector.", "danger")
        return redirect(url_for('tecnico_dashboard'))

    if request.method == 'POST':
        foto_rep = request.files.get('foto_reparado')
        if foto_rep and foto_rep.filename:
            p = guardar_foto(foto_rep)
            if p:
                reporte.foto_reparado_path = p
        try:
            reporte.estado = 'Reparado'
            if reporte.fecha_reparacion is None:
                reporte.fecha_reparacion = datetime.datetime.utcnow()
            db.session.commit()
            flash(f"Reporte de Patrulla #{reporte.id} actualizado a REPARADO.", "success")
            return redirect(url_for('admin_ver_patrullas') if current_user.role == 'Admin' else url_for('tecnico_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("Error al actualizar el reporte.", "danger")
            app.logger.error(f"Error al editar reporte de patrulla: {e}")
            return redirect(url_for('editar_reporte_patrulla', reporte_id=reporte.id))

    return render_template('editar_reporte_patrulla.html', reporte=reporte, user=current_user)


# ---------------------- ADMIN: CAMBIAR ESTADOS ----------------------

@app.route('/admin/reportes/patrulla/<int:reporte_id>/estado', methods=['POST'])
@login_required
def cambiar_estado_reporte_patrulla(reporte_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    try:
        nuevo_estado = request.form.get('estado')
        if nuevo_estado not in ['Pendiente', 'En Proceso', 'Cerrado']:
            flash('Estado no válido', 'danger')
            return redirect(url_for('admin_ver_patrullas'))
        reporte = PatrullaReporte.query.get_or_404(reporte_id)
        reporte.estado = nuevo_estado
        if nuevo_estado == 'Cerrado' and reporte.fecha_reparacion is None:
            reporte.fecha_reparacion = datetime.datetime.utcnow()
        db.session.commit()
        flash(f'Estado del reporte #{reporte_id} actualizado a "{nuevo_estado}"', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_ver_patrullas'))


@app.route('/admin/reportes/patrulla/<int:reporte_id>/eliminar', methods=['POST'])
@login_required
def eliminar_reporte_patrulla(reporte_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    try:
        reporte = PatrullaReporte.query.get_or_404(reporte_id)
        unidad = reporte.unidad_numero
        db.session.delete(reporte)
        db.session.commit()
        flash(f'Reporte de la unidad {unidad} eliminado correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_ver_patrullas'))


@app.route('/admin/reportes/equipo/<int:reporte_id>/estado', methods=['POST'])
@login_required
def cambiar_estado_reporte_equipo(reporte_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    try:
        nuevo_estado = request.form.get('estado')
        if nuevo_estado not in ['Pendiente', 'En Progreso', 'Reparado', 'Cerrado']:
            flash('Estado no válido', 'danger')
            return redirect(url_for('admin_ver_equipos'))
        reporte = EquipoReporte.query.get_or_404(reporte_id)
        reporte.estado = nuevo_estado
        if nuevo_estado in ['Reparado', 'Cerrado'] and reporte.fecha_reparacion is None:
            reporte.fecha_reparacion = datetime.datetime.utcnow()
        elif nuevo_estado in ['Pendiente', 'En Progreso']:
            reporte.fecha_reparacion = None
        db.session.commit()
        flash(f'Estado del reporte #{reporte_id} actualizado a "{nuevo_estado}"', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_ver_equipos'))


@app.route('/admin/eliminar/equipo/<int:reporte_id>', methods=['POST'])
@login_required
def admin_eliminar_reporte_equipo(reporte_id):
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    reporte = EquipoReporte.query.get_or_404(reporte_id)
    try:
        db.session.delete(reporte)
        db.session.commit()
        flash(f"Reporte de Equipo ID {reporte_id} eliminado.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error al eliminar el reporte.", "danger")
    return redirect(url_for('admin_ver_equipos'))


# ---------------------- API AJAX ----------------------

@app.route('/api/reportes/<int:reporte_id>/estado', methods=['PATCH'])
@login_required
def api_actualizar_estado_patrulla(reporte_id):
    if current_user.role != 'Admin':
        return jsonify({"error": "No autorizado"}), 403
    reporte = PatrullaReporte.query.get_or_404(reporte_id)
    data = request.get_json()
    if not data or 'estado' not in data:
        return jsonify({"error": "Datos inválidos"}), 400
    try:
        reporte.estado = data['estado']
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/reportes/<int:reporte_id>', methods=['DELETE'])
@login_required
def api_eliminar_reporte_patrulla(reporte_id):
    if current_user.role != 'Admin':
        return jsonify({"error": "No autorizado"}), 403
    reporte = PatrullaReporte.query.get_or_404(reporte_id)
    try:
        db.session.delete(reporte)
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ---------------------- VISTAS ADMIN ----------------------

@app.route('/admin/ver_equipos')
@login_required
def admin_ver_equipos():
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    reportes = db.session.query(EquipoReporte, User)\
        .join(User, EquipoReporte.user_id == User.id)\
        .order_by(EquipoReporte.fecha_reporte.desc())\
        .all()
    return render_template('admin_reportes_equipos.html', user=current_user, reportes=reportes)


@app.route('/admin/ver_patrullas')
@login_required
def admin_ver_patrullas():
    if current_user.role != 'Admin':
        return redirect(url_for('login'))
    reportes_patrulla = (
        db.session.query(PatrullaReporte, User)
        .join(User)
        .order_by(PatrullaReporte.fecha_reporte.desc())
        .all()
    )
    return render_template('admin_reportes_patrullas.html', user=current_user, reportes_patrulla=reportes_patrulla)


# ---------------------- INICIALIZACIÓN -------------3---------

with app.app_context():
    try:
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            nuevo_admin = User(username='admin', role='Admin', sector='Sistemas')
            nuevo_admin.set_password('admin123')
            db.session.add(nuevo_admin)
            db.session.commit()
            logger.info("✅ Administrador 'admin' creado.")
        else:
            logger.info("ℹ️ El administrador ya existe.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar: {e}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)