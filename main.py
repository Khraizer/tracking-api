import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
import brevo_python
from brevo_python.api.transactional_emails_api import TransactionalEmailsApi
from brevo_python.models.send_smtp_email import SendSmtpEmail
import time
import threading
import random
from datetime import datetime

# Configuración de la base de datos
db_config = {
    'user': '3bxBT4LXUabQUSz.root',
    'password': 'EhiX6MGEAXgOH7Ut',
    'host': 'gateway01.us-east-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'database': 'test'
}

# Modelos Pydantic
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    telefono: str
    placa: str
    tipo_vehiculo: str

class UserUpdate(BaseModel):
    email: str
    password: str
    telefono: str
    placa: str
    tipo_vehiculo: str
    oldEmail: str

class UserDelete(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    telefono: str
    placa: str
    tipo_vehiculo: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str


# Configuración de FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Función para generar datos de metadata aleatorios
def generate_metadata(user_id: int):
    while True:
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # 1. Verificar si existe metadata previa para este usuario
            cursor.execute("""
                SELECT id FROM metadata 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (user_id,))
            existing_record = cursor.fetchone()
            
            # Generar nuevos datos aleatorios
            latitud = 4.7110 + random.uniform(-0.1, 0.1)
            longitud = -74.0721 + random.uniform(-0.1, 0.1)
            velocidad = random.uniform(0, 120)
            inclinacion = random.uniform(-30, 30)
            contaminacion = random.uniform(0, 500)
            hora = datetime.now().strftime("%H:%M:%S")
            fecha = datetime.now().strftime("%Y-%m-%d")
            
            if existing_record:
                # 2. ACTUALIZAR el registro existente
                update_query = """
                UPDATE metadata 
                SET latitud = %s,
                    longitud = %s,
                    velocidad = %s,
                    inclinacion = %s,
                    contaminacion = %s,
                    hora = %s,
                    fecha = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                cursor.execute(update_query, (
                    latitud,
                    longitud,
                    velocidad,
                    inclinacion,
                    contaminacion,
                    hora,
                    fecha,
                    existing_record['id']
                ))
                print(f"Registro ACTUALIZADO para usuario {user_id}")
            else:
                # 3. CREAR un nuevo registro solo si no existe ninguno
                insert_query = """
                INSERT INTO metadata 
                (user_id, latitud, longitud, velocidad, inclinacion, contaminacion, hora, fecha)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    user_id,
                    latitud,
                    longitud,
                    velocidad,
                    inclinacion,
                    contaminacion,
                    hora,
                    fecha
                ))
                print(f"Nuevo registro CREADO para usuario {user_id}")
            
            connection.commit()
            
        except Exception as e:
            print(f"Error en generate_metadata: {str(e)}")
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
        
        # Esperar 2 minutos (120 segundos)
        time.sleep(120)
# Endpoints
@app.post("/login")
def login(user: UserLogin):
    print("\n=== PETICIÓN LOGIN RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (user.email, user.password))
        result = cursor.fetchone()

        if result:
            return {
                "message": "Login exitoso",
                "user": {
                    "id": result["id"],
                    "email": result["email"],   
                    "telefono": result["telefono"],
                    "placa": result["placa"],
                    "tipo_vehiculo": result["tipo_vehiculo"].decode('utf-8') if isinstance(result["tipo_vehiculo"], bytes) else result["tipo_vehiculo"]
                }
            }
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        connection.close()

@app.post("/register")
def register(user: UserRegister):
    print("\n=== PETICIÓN REGISTRO RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        INSERT INTO users (email, password, telefono, placa, tipo_vehiculo)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            user.email,
            user.password,
            user.telefono,
            user.placa,
            user.tipo_vehiculo
        ))
        connection.commit()

        if cursor.rowcount == 1:
            return {"message": "Usuario registrado exitosamente"}
        raise HTTPException(status_code=400, detail="Error al registrar usuario")
    
    except mysql.connector.Error as err:
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        raise HTTPException(status_code=500, detail=str(err))
    
    finally:
        cursor.close()
        connection.close()

@app.put("/update")
def update(user: UserUpdate):
    print("\n=== PETICIÓN ACTUALIZACIÓN RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        UPDATE users 
        SET email = %s, 
            password = %s,
            telefono = %s,
            placa = %s,
            tipo_vehiculo = %s
        WHERE email = %s
        """
        cursor.execute(query, (
            user.email,
            user.password,
            user.telefono,
            user.placa,
            user.tipo_vehiculo,
            user.oldEmail
        ))
        connection.commit()

        if cursor.rowcount == 1:
            return {"message": "Usuario actualizado exitosamente"}
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    except mysql.connector.Error as err:
        if err.errno == 1062:
            raise HTTPException(status_code=400, detail="El nuevo email ya está registrado")
        raise HTTPException(status_code=500, detail=str(err))
    
    finally:
        cursor.close()
        connection.close()

@app.get("/show")
def show():
    print("\n=== PETICIÓN SHOW RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = "SELECT id, email, telefono, placa, tipo_vehiculo FROM users"
        cursor.execute(query)
        users = cursor.fetchall()
        
        return {
            "message": "Lista de usuarios obtenida exitosamente",
            "users": users
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        connection.close()

from fastapi import HTTPException
from fastapi.responses import JSONResponse
import mysql.connector
from pydantic import BaseModel

class UserDelete(BaseModel):
    email: str
    password: str

@app.delete("/delete")
def delete_user(user: UserDelete):
    print(f"\n=== SOLICITUD DE ELIMINACIÓN PARA: {user.email} ===")
    
    connection = None
    cursor = None
    
    try:
        # 1. Establecer conexión con la base de datos
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # 2. Verificar que el usuario existe
        cursor.execute("SELECT email, password FROM users WHERE email = %s", (user.email,))
        db_user = cursor.fetchone()
        
        if not db_user:
            print(f"Usuario no encontrado: {user.email}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "El usuario no existe en nuestro sistema"
                }
            )
        
        # 3. Verificar contraseña (sin hash)
        if user.password != db_user['password']:
            print("Contraseña incorrecta")
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "message": "Contraseña incorrecta"
                }
            )
        
        # 4. Eliminar el usuario
        cursor.execute("DELETE FROM users WHERE email = %s", (user.email,))
        connection.commit()
        
        # 5. Verificar que se eliminó correctamente
        if cursor.rowcount == 1:
            print(f"Usuario eliminado: {user.email}")
            
            # Eliminar tokens asociados si existen
            try:
                cursor.execute("DELETE FROM password_tokens WHERE email = %s", (user.email,))
                connection.commit()
                print("Tokens asociados eliminados")
            except Exception as token_error:
                print(f"Error eliminando tokens: {str(token_error)}")
            
            return {
                "status": "success",
                "message": "Cuenta eliminada permanentemente"
            }
        else:
            print("No se pudo eliminar el usuario")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "No se pudo completar la eliminación"
                }
            )
            
    except mysql.connector.Error as db_error:
        print(f"Error de base de datos: {str(db_error)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error en la base de datos",
                "error": str(db_error)
            }
        )
        
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error interno del servidor",
                "error": str(e)
            }
        )
        
    finally:
        # Cerrar conexiones siempre
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("Conexión a BD cerrada")


@app.post("/forgot_password")
def forgot_password(request: ForgotPasswordRequest):
    print("\n=== PETICIÓN OLVIDÉ MI CONTRASEÑA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Verificamos que el correo exista
        cursor.execute("SELECT * FROM users WHERE email = %s", (request.email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Correo no registrado")

        # Generar un token aleatorio
        token = str(random.randint(100000, 999999))

        # Guardar el token en la tabla
        cursor.execute("""
            INSERT INTO password_tokens (email, token, created_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE token = VALUES(token), created_at = NOW()
        """, (request.email, token))
        connection.commit()

        # Cargar variables de entorno
        load_dotenv()

        # Configuración del correo con plantilla sofisticada
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
        api_instance = TransactionalEmailsApi(brevo_python.ApiClient(configuration))

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔑 Recuperación de Contraseña - TrackingApp</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');
        
        body {{
            font-family: 'Poppins', sans-serif;
            line-height: 1.6;
            color: #2d3748;
            background-color: #f7fafc;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        
        .email-container {{
            max-width: 600px;
            width: 100%;
            margin: 20px;
        }}
        
        .email-card {{
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            text-align: center;
        }}
        
        .email-header {{
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            padding: 40px 20px;
            color: white;
        }}
        
        .email-header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .email-icon {{
            font-size: 48px;
            margin-bottom: 20px;
            display: block;
        }}
        
        .email-body {{
            padding: 40px;
        }}
        
        .welcome-text {{
            font-size: 18px;
            color: #4a5568;
            margin-bottom: 30px;
            line-height: 1.7;
        }}
        
        .code-container {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 30px;
            margin: 30px 0;
            border: 1px dashed #e2e8f0;
        }}
        
        .code-title {{
            font-size: 16px;
            color: #718096;
            margin-bottom: 15px;
        }}
        
        .verification-code {{
            font-size: 36px;
            font-weight: 600;
            letter-spacing: 5px;
            color: #4f46e5;
            margin: 15px 0;
            padding: 10px;
            background: white;
            border-radius: 8px;
            display: inline-block;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
        }}
        
        .expiration {{
            color: #e53e3e;
            font-weight: 500;
            font-size: 14px;
            margin-top: 10px;
        }}
        
        .instructions {{
            font-size: 15px;
            color: #4a5568;
            margin: 30px 0;
            line-height: 1.7;
        }}
        
        .email-footer {{
            background: #f1f5f9;
            padding: 25px;
            font-size: 13px;
            color: #64748b;
        }}
        
        .social-links {{
            margin: 20px 0;
            font-size: 24px;
        }}
        
        .social-links a {{
            color: #4f46e5;
            margin: 0 10px;
            text-decoration: none;
        }}
        
        .copyright {{
            margin-top: 15px;
            font-size: 12px;
        }}
        
        .contact-link {{
            color: #4f46e5;
            text-decoration: none;
            font-weight: 500;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-card">
            <div class="email-header">
                <span class="email-icon">🔐</span>
                <h1>Recupera tu Acceso</h1>
            </div>
            
            <div class="email-body">
                <p class="welcome-text">
                    Hola, hemos recibido una solicitud para restablecer tu contraseña en 
                    <strong>TrackingApp</strong>. Por favor utiliza el siguiente código de verificación:
                </p>
                
                <div class="code-container">
                    <div class="code-title">TU CÓDIGO DE VERIFICACIÓN</div>
                    <div class="verification-code">{token}</div>
                    <div class="expiration">⚠️ Válido por 15 minutos ⚠️</div>
                </div>
                
                <p class="instructions">
                    Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura.
                    Si tienes dudas, contáctanos respondiendo este correo.
                </p>
            </div>
            
            <div class="email-footer">
                <div class="social-links">
                    <a href="#">📱</a>
                    <a href="#">💻</a>
                    <a href="#">📧</a>
                </div>
                <p>
                    ¿Necesitas ayuda? <a href="mailto:soporte@trackingapp.com" class="contact-link">✉️ Contáctanos</a>
                </p>
                <p class="copyright">
                    © {datetime.now().year} TrackingApp. Todos los derechos reservados.<br>
                    <a href="https://trackingapp.com" style="color: #4f46e5;">🌐 trackingapp.com</a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

        email_data = SendSmtpEmail(
            to=[{"email": request.email}],
            subject="🔑 Código para restablecer tu contraseña - TrackingApp",
            html_content=html_content,
            sender={"name": "TrackingApp", "email": "miguelararat999@gmail.com"},
            reply_to={"email": "soporte@trackingapp.com", "name": "Soporte TrackingApp"}
        )

        # Enviar el correo
        api_instance.send_transac_email(email_data)

        return {
            "message": "Se ha enviado un código de recuperación al correo",
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error al procesar la solicitud",
                "error": str(e)
            }
        )

    finally:
        cursor.close()
        connection.close()

@app.post("/reset_password")
def reset_password(request: ResetPasswordRequest):
    print("\n=== PETICIÓN RESTABLECER CONTRASEÑA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Validar token
        cursor.execute("""
            SELECT * FROM password_tokens 
            WHERE email = %s AND token = %s 
            AND TIMESTAMPDIFF(MINUTE, created_at, NOW()) <= 15
        """, (request.email, request.token))
        token_data = cursor.fetchone()

        if not token_data:
            raise HTTPException(status_code=400, detail="Token invalido o expirado")

        # Actualizar contraseña
        cursor.execute("""
            UPDATE users 
            SET password = %s 
            WHERE email = %s
        """, (request.new_password, request.email))
        connection.commit()

        # Eliminar token después del uso
        cursor.execute("DELETE FROM password_tokens WHERE email = %s", (request.email,))
        connection.commit()

        return {"message": "Contraseña actualizada correctamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        connection.close()

@app.post("/start_metadata/{user_id}")
def start_metadata_generation(user_id: int, background_tasks: BackgroundTasks):
    print("\n=== INICIANDO GENERACIÓN DE METADATA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Iniciar el generador de metadata en segundo plano
        background_tasks.add_task(generate_metadata, user_id)
        return {"message": f"Generación de metadata iniciada para usuario {user_id}"}
    
    finally:
        cursor.close()
        connection.close()

@app.get("/metadata/{user_id}")
def get_metadata(user_id: int):
    print("\n=== PETICIÓN METADATA RECIBIDA ===")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT * FROM metadata 
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 100
        """
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        
        return {
            "message": f"Metadata para usuario {user_id}",
            "count": len(results),
            "data": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        connection.close()

@app.get("/")
def read_root():
    return {"message": "API de gestión de usuarios"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)