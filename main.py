from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
from mysql.connector import Error
from typing import Optional, List  # Importando List correctamente
from datetime import datetime

# Configuración de la base de datos
db_config = {
    'user': '3bxBT4LXUabQUSz.root',
    'password': 'EhiX6MGEAXgOH7Ut',
    'host': 'gateway01.us-east-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'database': 'test'
}

# Definición del modelo Metadata antes de la ruta GET
class MetadataCreate(BaseModel):
    user_id: int
    latitud: float
    longitud: float
    velocidad: Optional[float]
    inclinacion: Optional[float]
    contaminacion: Optional[float]
    hora: str
    fecha: str

# Definición del modelo de regulación
class ArduinoRequest(BaseModel):
    valor: float 

# Definición de Metadata (asegúrate de que esta clase está antes de la ruta)
class Metadata(BaseModel):
    user_id: int
    latitud: float
    longitud: float
    velocidad: Optional[float]
    inclinacion: Optional[float]
    contaminacion: Optional[float]
    hora: str
    fecha: str

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

# Endpoint para insertar metadatos a la Base de Datos
@app.post("/metadata")
def insert_metadata(data: MetadataCreate):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        insert_query = """
            INSERT INTO metadata 
            (user_id, latitud, longitud, velocidad, inclinacion, contaminacion, hora, fecha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            data.user_id,
            data.latitud,
            data.longitud,
            data.velocidad,
            data.inclinacion,
            data.contaminacion,
            data.hora,
            data.fecha
        ))
        connection.commit()
        return {"message": "Metadata insertada exitosamente"}

    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error al insertar metadata: {str(e)}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
            
# Endpoint para que el modelo de IA obtenga el historico de metadatos de un vehículo.
@app.get("/metadata/{user_id}", response_model=List[Metadata])  # Usando Metadata correctamente
def get_metadata(user_id: int):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        select_query = """
            SELECT user_id, latitud, longitud, velocidad, inclinacion, contaminacion, hora, fecha
            FROM metadata
            WHERE user_id = %s
            ORDER BY fecha ASC, hora ASC
        """
        cursor.execute(select_query, (user_id,))
        records = cursor.fetchall()

        if not records:
            raise HTTPException(status_code=404, detail="No se encontraron metadatos para este usuario")

        metadata_list = [Metadata(**record) for record in records]
        return metadata_list

    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error al recuperar los metadatos: {str(e)}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

# Endpoint para recibir la variable y enviarla a otro lugar
@app.post("/send-to-arduino")
async def send_to_arduino(data: ArduinoRequest):
    try:
        response = requests.post("http://pendiente-arduino", json={"valor": data.valor})
        
        if response.status_code == 200:
            return {"message": "Datos enviados correctamente al dispositivo Arduino", "status": "success"}
        else:
            raise HTTPException(status_code=500, detail="Error al enviar los datos a Arduino")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error al realizar la solicitud: {str(e)}")



@app.get("/")
def read_root():
    return {"message": "API de Metadatos"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
