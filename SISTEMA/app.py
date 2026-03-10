import os
import logging
import datetime  # Importado correctamente para evitar el NameError
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash 
from flask_login import login_required

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BD ---
database_url = os.environ.get('DATABASE_URL')

logger.info(f"--- Intentando conectar con DATABASE_URL detectada ---")

if database_url:
    # Ajuste de protocolo para Railway
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info("Configuración exitosa: Usando base de datos remota de Railway.")
else:
    logger.warning("!!! AVISO: No se detectó DATABASE_URL. Usando localhost. !!!")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/SISTEMA'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_segura_tickets') 

db = SQLAlchemy(app)

# --- CONFIGURACIÓN DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Carpeta de fotos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Carpeta de fotos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------- VARIABLES GLOBALES (ROLES) ----------------------
ROLES_DISPONIBLES = ['Admin', 'Tecnico', 'Usuario'] 


# --- FUNCIONES ÚTILES ---
def guardar_foto(file):
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # Generar un nombre de archivo único basado en la fecha y hora
        unique_filename = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            file.save(filepath)
            if os.path.getsize(filepath) == 0:
                os.remove(filepath)
                return None
            return os.path.join('uploads', unique_filename).replace('\\', '/')
        except Exception as e:
            current_app.logger.error(f"Error al guardar archivo: {e}")
            return None
    return None 


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow}


# --- MODELOS ---
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

class EquipoReporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- NUEVOS CAMPOS ---
    responsable_nombre = db.Column(db.String(100), nullable=False)
    responsable_sector = db.Column(db.String(100), nullable=False)
    telefono_responsable = db.Column(db.String(20), nullable=False)
    # ---------------------

    sector = db.Column(db.String(50), nullable=False)
    inventario_numero = db.Column(db.String(50), nullable=False)
    falla_descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), default='Pendiente')
    fecha_reporte = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fecha_reparacion = db.Column(db.DateTime, nullable=True)
    foto_falla_path = db.Column(db.String(255), nullable=True)
    foto_reparado_path = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('equipo_reportes', lazy=True))

class PatrullaReporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    unidad_numero = db.Column(db.String(50), nullable=False)
    sector = db.Column(db.String(50), nullable=False)
    
    # ------------------ CAMPOS DE INFORMACIÓN BÁSICA ------------------
    oficial_nombre = db.Column(db.String(100), nullable=False) 
    placa = db.Column(db.String(20), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    turno = db.Column(db.String(20), nullable=False)
    
    # ------------------ ESTADO DE CÁMARAS Y GRABADORAS ------------------
    camara1_funciona = db.Column(db.Boolean, default=True)
    camara2_funciona = db.Column(db.Boolean, default=True)
    camara3_funciona = db.Column(db.Boolean, default=True)
    camara4_funciona = db.Column(db.Boolean, default=True)
    
    grabadora1_funciona = db.Column(db.Boolean, default=True)
    grabadora2_funciona = db.Column(db.Boolean, default=True)
    grabadora3_funciona = db.Column(db.Boolean, default=True)
    grabadora4_funciona = db.Column(db.Boolean, default=True)

    # ------------------ DESCRIPCIONES Y EVIDENCIAS DE FALLAS ------------------
    # Fallas de Cámara
    falla_camara_desc_1 = db.Column(db.Text, nullable=True) 
    falla_camara_foto_1 = db.Column(db.String(255), nullable=True) 
    falla_camara_desc_2 = db.Column(db.Text, nullable=True) 
    falla_camara_foto_2 = db.Column(db.String(255), nullable=True) 
    falla_camara_desc_3 = db.Column(db.Text, nullable=True) 
    falla_camara_foto_3 = db.Column(db.String(255), nullable=True) 
    falla_camara_desc_4 = db.Column(db.Text, nullable=True) 
    falla_camara_foto_4 = db.Column(db.String(255), nullable=True) 

    # Fallas de Grabadora
    falla_grabadora_desc_1 = db.Column(db.Text, nullable=True) 
    falla_grabadora_foto_1 = db.Column(db.String(255), nullable=True) 
    falla_grabadora_desc_2 = db.Column(db.Text, nullable=True) 
    falla_grabadora_foto_2 = db.Column(db.String(255), nullable=True) 
    falla_grabadora_desc_3 = db.Column(db.Text, nullable=True) 
    falla_grabadora_foto_3 = db.Column(db.String(255), nullable=True) 
    falla_grabadora_desc_4 = db.Column(db.Text, nullable=True) 
    falla_grabadora_foto_4 = db.Column(db.String(255), nullable=True) 

    # Observaciones generales
    observaciones = db.Column(db.Text, nullable=True)
    
    # ------------------ CAMPOS DE GESTIÓN ------------------
    falla_descripcion = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='Pendiente')
    fecha_reporte = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    fecha_reparacion = db.Column(db.DateTime, nullable=True)
    foto_falla_path = db.Column(db.String(255), nullable=True)
    foto_reparado_path = db.Column(db.String(255), nullable=True)

    user = db.relationship('User', backref=db.backref('patrulla_reportes', lazy=True))


# --------------------- RUTAS BÁSICAS ------------------------

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
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Credenciales inválidas', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    if current_user.role == 'Tecnico':
        return redirect(url_for('tecnico_dashboard'))
    return redirect(url_for('oficial_dashboard'))


# ---------------------- DASHBOARD ADMIN ----------------------

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))
    return render_template('admin_dashboard.html', user=current_user)


# ---------------------- ADMIN USUARIOS ----------------------

@app.route('/admin/usuarios', methods=['GET', 'POST'])
@login_required
def admin_usuarios():
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))
    
    # Lógica de CREACIÓN (POST)
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '').strip()
        sector = request.form.get('sector', '').strip()
        
        # Validaciones
        if not username or not password or not role:
            flash('Usuario, contraseña y rol son obligatorios.', 'danger')
            usuarios = User.query.order_by(User.username).all()
            return render_template('admin_usuarios.html', user=current_user, usuarios=usuarios, roles=ROLES_DISPONIBLES)

        usuario_existente = User.query.filter_by(username=username).first()
        if usuario_existente:
            flash('El nombre de usuario ya existe.', 'danger')
            usuarios = User.query.order_by(User.username).all()
            return render_template('admin_usuarios.html', user=current_user, usuarios=usuarios, roles=ROLES_DISPONIBLES)
        
        try:
            nuevo_usuario = User(
                username=username,
                role=role,
                sector=sector if sector else None
            )
            nuevo_usuario.set_password(password)
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            flash(f'Usuario "{username}" creado exitosamente.', 'success')
            return redirect(url_for('admin_usuarios')) 
            
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el usuario.', 'danger')
            current_app.logger.error(f"Error al crear usuario: {e}")

    # Lógica de VISUALIZACIÓN (GET)
    usuarios = User.query.order_by(User.username).all()
    
    return render_template('admin_usuarios.html', 
                           user=current_user, 
                           usuarios=usuarios,
                           roles=ROLES_DISPONIBLES)


@app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_editar_usuario(user_id):
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))
    
    usuario = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        role = request.form.get('role', '').strip()
        sector = request.form.get('sector', '').strip()
        nueva_password = request.form.get('password', '').strip()
        
        if not username or not role:
            flash('Usuario y rol son obligatorios.', 'danger')
            return render_template('admin_editar_usuario.html', user=current_user, usuario=usuario, roles=ROLES_DISPONIBLES)
        
        usuario_existente = User.query.filter_by(username=username).first()
        if usuario_existente and usuario_existente.id != user_id:
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
            current_app.logger.error(f"Error al editar usuario: {e}")
    
    return render_template('admin_editar_usuario.html', 
                           user=current_user, 
                           usuario=usuario, 
                           roles=ROLES_DISPONIBLES)


@app.route('/admin/usuarios/eliminar/<int:user_id>', methods=['POST'])
@login_required
def admin_eliminar_usuario(user_id):
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))
    
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
        current_app.logger.error(f"Error al eliminar usuario: {e}")
    
    return redirect(url_for('admin_usuarios'))


# ---------------------- DASHBOARD OFICIAL ----------------------

@app.route('/oficial/dashboard')
@login_required
def oficial_dashboard():
    if current_user.role != 'Usuario': 
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))
    return render_template('usuario_dashboard.html', user=current_user)


# ---------------------- DASHBOARD TECNICO ----------------------

@app.route('/tecnico/dashboard')
@login_required
def tecnico_dashboard():
    if current_user.role != 'Tecnico':
        flash("Acceso denegado. Rol incorrecto.", "danger")
        return redirect(url_for('dashboard'))

    base_query_equipo = EquipoReporte.query.filter(
        EquipoReporte.estado.in_(['Pendiente', 'En Progreso'])
    )
    
    base_query_patrulla = PatrullaReporte.query.filter(
        PatrullaReporte.estado.in_(['Pendiente', 'En Progreso'])
    )
    
    sector_filtro = current_user.sector
    
    current_app.logger.info(f"--- Diagnóstico Técnico Dashboard ---")
    current_app.logger.info(f"Técnico: {current_user.username}, Sector: '{sector_filtro}'")

    if sector_filtro and sector_filtro != 'Global':
        current_app.logger.info(f"Aplicando filtro por sector: '{sector_filtro}'")
        base_query_equipo = base_query_equipo.filter_by(sector=sector_filtro)
        base_query_patrulla = base_query_patrulla.filter_by(sector=sector_filtro)
    else:
        current_app.logger.info("El técnico es 'Global' o su sector es nulo. Se mostrarán todos los sectores.")

    pendientes_equipo = base_query_equipo.order_by(EquipoReporte.fecha_reporte.asc()).all()
    pendientes_patrulla = base_query_patrulla.order_by(PatrullaReporte.fecha_reporte.asc()).all()
    
    current_app.logger.info(f"Resultados: Equipos: {len(pendientes_equipo)}, Patrullas: {len(pendientes_patrulla)}")

    return render_template('tecnico_dashboard.html', 
                           user=current_user, 
                           pendientes_equipo=pendientes_equipo,
                           pendientes_patrulla=pendientes_patrulla)


# ---------------------- REPORTE EQUIPO ----------------------
@app.route('/reporte_equipo', methods=['GET', 'POST'])
@login_required
def reporte_equipo_form():
    if request.method == 'POST':
        # 1. Capturar datos del formulario (deben coincidir con el 'name' del HTML)
        resp_nom = request.form.get('responsable_nombre')
        resp_sec = request.form.get('responsable_sector')
        resp_tel = request.form.get('telefono_responsable')
        tipo_equipo = request.form.get('tipo')
        num_serie = request.form.get('serie')
        est_operativo = request.form.get('estado_operativo') # Cambiado para coincidir con el nuevo HTML
        comentarios = request.form.get('comentarios')

        # 2. Validación básica de seguridad
        if not all([resp_nom, resp_sec, resp_tel, tipo_equipo, num_serie, est_operativo, comentarios]):
            flash("Error: Todos los campos marcados con (*) son obligatorios.", "danger")
            return render_template('reporte_equipo_form.html')

        try:
            # 3. Crear el objeto con los nombres exactos del Modelo
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
            print(f"DEBUG ERROR: {e}") # Esto saldrá en tu terminal de VS Code
            flash(f"Error al guardar en la base de datos: {str(e)}", "danger")
    
    return render_template('reporte_equipo_form.html')
# ---------------------- REPORTE PATRULLA ----------------------
# ---------------------- REPORTE PATRULLA (SOLO TÉCNICOS) ----------------------

@app.route('/reporte/patrulla', methods=['GET', 'POST'])
@login_required
def reporte_patrulla_form():
    # Bloqueo de seguridad: Solo Técnicos y Administradores
    if current_user.role not in ['Tecnico', 'Admin']:
        flash('Acceso denegado. Solo el personal técnico puede realizar inspecciones.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # Captura de datos básicos de la unidad
            unidad_numero = request.form.get('unidad_numero', '').strip()
            oficial_nombre = request.form.get('oficial_nombre', '').strip()
            placa = request.form.get('placa', '').strip()
            marca = request.form.get('marca', '').strip()
            modelo = request.form.get('modelo', '').strip()
            turno = request.form.get('turno', '').strip()
            sector_unidad = request.form.get('sector', '').strip()
            fecha_reporte_str = request.form.get('fecha_reporte')
            
            # Validación de campos obligatorios
            if not all([unidad_numero, oficial_nombre, placa, marca, modelo, turno, sector_unidad]):
                flash('Faltan campos obligatorios en la información de la unidad.', 'danger')
                return render_template('reporte_patrulla_form.html', user=current_user)

            # Conversión de fecha
            try:
                fecha_reporte = datetime.datetime.fromisoformat(fecha_reporte_str) 
            except ValueError:
                fecha_reporte = datetime.datetime.now()

            todas_ok = True
            falla_lista = []
            componentes_status = {}
            componentes_detalle = {}
            primera_foto_global = None

            # Procesamiento de Cámaras (1 a 4) y Grabadoras (1 a 4)
            for i in range(1, 5):
                # Lógica para Cámaras
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

                # Lógica para Grabadoras
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
            
            # El estado depende de si el técnico encontró fallas o no
            estado = "Pendiente" if not todas_ok else "Cerrado" 

            nuevo_reporte = PatrullaReporte(
                user_id=current_user.id, # ID del TÉCNICO que llena el reporte
                unidad_numero=unidad_numero,
                sector=sector_unidad,    # Sector de la patrulla revisada
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
            current_app.logger.error(f"Error en reporte técnico: {e}")
            flash("Error al procesar la inspección.", "danger")
            return render_template('reporte_patrulla_form.html', user=current_user)

    return render_template('reporte_patrulla_form.html', user=current_user)

# ---------------------- MIS REPORTES ----------------------

@app.route('/mis_reportes')
@login_required
def mis_reportes():
    if current_user.role != 'Usuario':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    equipos = EquipoReporte.query.filter_by(user_id=current_user.id).order_by(EquipoReporte.fecha_reporte.desc()).all()
    patrullas = PatrullaReporte.query.filter_by(user_id=current_user.id).order_by(PatrullaReporte.fecha_reporte.desc()).all()

    return render_template('mis_reportes.html', user=current_user,
                           equipos=equipos, patrullas=patrullas)


# ---------------------- EDITAR REPORTE DE EQUIPO (TEC/ADMIN) ----------------------

# ---------------------- EDITAR REPORTE DE EQUIPO (TEC/ADMIN) ----------------------

# ---------------------- EDITAR REPORTE DE EQUIPO (VERSION FINAL) ----------------------

@app.route('/reporte/equipo/editar/<int:reporte_id>', methods=['GET', 'POST'])
@login_required
def editar_reporte_equipo(reporte_id):
    # 1. Validación de Roles
    if current_user.role not in ['Admin', 'Tecnico']:
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))

    reporte = EquipoReporte.query.get_or_404(reporte_id)

    # 2. Procesar Actualización (POST)
    if request.method == 'POST':
        try:
            # Obtener el nuevo estado del formulario
            nuevo_estado = request.form.get('estado')
            if nuevo_estado:
                reporte.estado = nuevo_estado
                
                # Gestión de fecha de reparación
                if nuevo_estado in ['Reparado', 'Cerrado']:
                    reporte.fecha_reparacion = datetime.datetime.utcnow()
                else:
                    reporte.fecha_reparacion = None

            # Procesar foto de reparación
            foto_rep = request.files.get('foto_reparado')
            if foto_rep and foto_rep.filename != '':
                path_foto = guardar_foto(foto_rep)
                if path_foto:
                    reporte.foto_reparado_path = path_foto

            db.session.commit()
            flash(f"✅ Reporte #{reporte_id} actualizado con éxito.", "success")
            
            # Redirigir según el rol
            if current_user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('tecnico_dashboard'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al editar equipo ID {reporte_id}: {e}")
            flash("❌ Error al guardar los cambios.", "danger")
            return redirect(url_for('tecnico_dashboard'))

    # Si es GET, enviamos a la página de edición (si tienes una dedicada)
    # o simplemente redirigimos al dashboard si lo haces por modales
    return render_template('editar_reporte_equipo.html', reporte=reporte)
# ---------------------- EDITAR REPORTE DE PATRULLA (TEC/ADMIN) ----------------------

@app.route('/reporte/patrulla/editar/<int:reporte_id>', methods=['GET', 'POST'])
@login_required
def editar_reporte_patrulla(reporte_id):
    if current_user.role not in ['Admin', 'Tecnico']:
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))

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
            
            if current_user.role == 'Admin':
                return redirect(url_for('admin_ver_patrullas'))
            return redirect(url_for('tecnico_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash("Error al actualizar el reporte.", "danger")
            current_app.logger.error(f"Error al editar reporte de patrulla: {e}")
            return redirect(url_for('editar_reporte_patrulla', reporte_id=reporte.id))

    return render_template('editar_reporte_patrulla.html', reporte=reporte, user=current_user)


# ---------------------- CAMBIAR ESTADO DE REPORTE DE PATRULLA ----------------------

@app.route('/admin/reportes/patrulla/<int:reporte_id>/estado', methods=['POST'])
@login_required
def cambiar_estado_reporte_patrulla(reporte_id):
    if current_user.role != 'Admin':
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        nuevo_estado = request.form.get('estado')
        
        estados_validos = ['Pendiente', 'En Proceso', 'Cerrado']
        if nuevo_estado not in estados_validos:
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
        flash(f'Error al actualizar el estado: {str(e)}', 'danger')
        current_app.logger.error(f"Error al cambiar estado de reporte patrulla: {e}")
    
    return redirect(url_for('admin_ver_patrullas'))


# ---------------------- ELIMINAR REPORTE DE PATRULLA ----------------------

@app.route('/admin/reportes/patrulla/<int:reporte_id>/eliminar', methods=['POST'])
@login_required
def eliminar_reporte_patrulla(reporte_id):
    if current_user.role != 'Admin':
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        reporte = PatrullaReporte.query.get_or_404(reporte_id)
        unidad = reporte.unidad_numero
        
        db.session.delete(reporte)
        db.session.commit()
        
        flash(f'Reporte de la unidad {unidad} (ID #{reporte_id}) eliminado correctamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el reporte: {str(e)}', 'danger')
        current_app.logger.error(f"Error al eliminar reporte de patrulla: {e}")
    
    return redirect(url_for('admin_ver_patrullas'))


# ---------------------- CAMBIAR ESTADO DE REPORTE DE EQUIPO ----------------------

@app.route('/admin/reportes/equipo/<int:reporte_id>/estado', methods=['POST'])
@login_required
def cambiar_estado_reporte_equipo(reporte_id):
    if current_user.role != 'Admin':
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        nuevo_estado = request.form.get('estado')
        
        estados_validos = ['Pendiente', 'En Progreso', 'Reparado', 'Cerrado']
        if nuevo_estado not in estados_validos:
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
        flash(f'Error al actualizar el estado: {str(e)}', 'danger')
        current_app.logger.error(f"Error al cambiar estado de reporte equipo: {e}")
    
    return redirect(url_for('admin_ver_equipos'))


## ---------------------- API PARA REPORTES DE PATRULLAS (AJAX) ----------------------

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
        return jsonify({"success": True, "message": "Estado actualizado correctamente"}), 200
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
        return jsonify({"success": True, "message": "Reporte eliminado"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ---------------------- ELIMINAR REPORTE DE EQUIPO ----------------------

@app.route('/admin/eliminar/equipo/<int:reporte_id>', methods=['POST'])
@login_required
def admin_eliminar_reporte_equipo(reporte_id):
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))

    reporte = EquipoReporte.query.get_or_404(reporte_id)

    try:
        db.session.delete(reporte)
        db.session.commit()
        flash(f"Reporte de Equipo ID {reporte_id} eliminado permanentemente.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash("Error al intentar eliminar el reporte.", "danger")
        current_app.logger.error(f"Error al eliminar reporte de equipo: {e}")
        
    return redirect(url_for('admin_ver_equipos'))


# ---------------------- VER EQUIPOS ADMIN ----------------------
@app.route('/admin/ver_equipos')
@login_required
def admin_ver_equipos():
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))

    reportes = db.session.query(EquipoReporte, User)\
        .join(User, EquipoReporte.user_id == User.id)\
        .order_by(EquipoReporte.fecha_reporte.desc())\
        .all()

    return render_template('admin_reportes_equipos.html', 
                            user=current_user, 
                            reportes=reportes)

# ---------------------- VER PATRULLAS ADMIN ----------------------

@app.route('/admin/ver_patrullas')
@login_required
def admin_ver_patrullas():
    if current_user.role != 'Admin':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('dashboard'))

    reportes_patrulla = (
        db.session.query(PatrullaReporte, User)
        .join(User)
        .order_by(PatrullaReporte.fecha_reporte.desc())
        .all()
    )

    return render_template(
        'admin_reportes_patrullas.html',
        user=current_user,
        reportes_patrulla=reportes_patrulla
    )

# ---------------------- ADMIN INICIAL ----------------------

def crear_admin_inicial():
    with app.app_context():
        db.create_all() 
        admin = User.query.filter_by(username='admin').first()

        if admin is None:
            admin = User(username='admin', role='Admin', sector='Administracion Central')
            admin.set_password('adminpass')
            db.session.add(admin)
            
            # ... (tus técnicos y oficiales)

            db.session.commit()
            print("ADMIN CREADO -> usuario: admin  pass: adminpass")

# ---------------------- RUN ----------------------
# ---------------------- INICIALIZACIÓN DE BD Y ADMIN ----------------------
with app.app_context():
    try:
        db.create_all()
        admin_root = User.query.filter_by(username='admin').first()
        
        if not admin_root:
            nuevo_admin = User(
                username='admin', 
                role='Admin', 
                sector='Soporte'
            )
            nuevo_admin.set_password('admin123') 
            db.session.add(nuevo_admin)
            db.session.commit()
            logger.info("¡ADMINISTRADOR CREADO EXITOSAMENTE!")
        else:
            logger.info("El administrador ya existe en la base de datos.")
    except Exception as e:
        logger.error(f"Error inicializando la base de datos: {e}")

# ---------------------- EJECUCIÓN ----------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)