from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta
import sqlite3
import logging
import uuid
import hashlib


conn = sqlite3.connect("contactos.db")
app = FastAPI()

security = HTTPBearer()
security_basic = HTTPBasic()

origins = [
    "http://127.0.0.1:5000",
    "https://contacts-frontend-be92669e2c94.herokuapp.com",
    "https://jesusraul.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)   


class Contacto(BaseModel):
    email: str
    nombre: str
    telefono: str



@app.post("/register/")
def register(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales faltantes")

    username = credentials.username
    password = credentials.password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM usuarios WHERE username=?', (username,))
        existing_user = c.fetchone()

        if existing_user:
            return {"error": "El usuario ya existe"}

        c.execute(
            'INSERT INTO usuarios (username, password) VALUES (?, ?)',
            (username, hashed_password)
        )
        conn.commit()

    return {"status": "Usuario registrado con éxito"}

@app.get("/login")
def login(credentials: HTTPBearer = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Acceso denegado: Token faltante")

    token = credentials.credentials

    current_timestamp = datetime.utcnow().timestamp()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username, expiration_timestamp FROM usuarios WHERE token=?', (token,))
        user_data = c.fetchone()

        if user_data and current_timestamp < user_data[1]:
            return {"mensaje": "Acceso permitido"}
        else:
            raise HTTPException(status_code=401, detail="Acceso denegado: Token inválido o expirado")

@app.get("/token/")
def generate_token(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales faltantes")

    username = credentials.username
    password = credentials.password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    with sqlite3.connect("contactos.db") as conn:
        c = conn.cursor()
        c.execute('SELECT username, password FROM usuarios WHERE username=?', (username,))
        user = c.fetchone()

        if user and user[1] == hashed_password:
            timestamp = conn.execute('SELECT strftime("%s", "now")').fetchone()[0]
            token = hashlib.sha256((username + str(uuid.uuid4())).encode()).hexdigest()
            expiration_time = timedelta(minutes=1)  # Cambiar la duración a 1 minuto
            expiration_timestamp = (datetime.utcnow() + expiration_time).timestamp()
            c.execute(
                'UPDATE usuarios SET token=?, timestamp=?, expiration_timestamp=? WHERE username=?',
                (token, timestamp, expiration_timestamp, username)
            )
            conn.commit()
            
            response_data = {
                "token": token
            }
            return JSONResponse(content=response_data)
        else:
            raise HTTPException(status_code=401, detail="Acceso denegado: Credenciales inválidas")


@app.get("/contactos")
async def obtener_contactos(token: str = Depends(login)):
    c = conn.cursor()
    c.execute('SELECT * FROM contactos;')
    response = []
    for row in c:
        contacto = {"email":row[0],"nombre":row[1], "telefono":row[2]}
        response.append(contacto)
    return response


@app.post("/contactos")
async def crear_contacto(contacto: Contacto, token: str = Depends(login)):
    try:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM contactos WHERE email = ?', (contacto.email,))
        count = c.fetchone()[0]

        if count > 0:
            raise HTTPException(status_code=400, detail="El contacto ya existe")

        c.execute('INSERT INTO contactos (email, nombre, telefono) VALUES (?, ?, ?)',
                  (contacto.email, contacto.nombre, contacto.telefono))
        conn.commit()
        
        return contacto
    
    except Exception as e:
        logging.error(str(e))
        raise HTTPException(status_code=500, detail="Error de servidor")



@app.get("/contactos/{email}")
async def obtener_contacto(email: str, token: str = Depends(login)):
    c = conn.cursor()
    c.execute('SELECT * FROM contactos WHERE email = ?', (email,))
    contacto = None
    for row in c:
        contacto = {"email":row[0],"nombre":row[1],"telefono":row[2]}
    if contacto is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    return contacto


@app.put("/contactos/{email}")
async def actualizar_contacto(email: str, contacto: Contacto, token: str = Depends(login)):
    c = conn.cursor()
    c.execute('UPDATE contactos SET nombre = ?, telefono = ? WHERE email = ?',
              (contacto.nombre, contacto.telefono, email))
    conn.commit()
    return contacto

@app.delete("/contactos/{email}")
async def eliminar_contacto(email: str, token: str = Depends(login)):
    c = conn.cursor()
    c.execute('DELETE FROM contactos WHERE email = ?', (email,))
    conn.commit()
    return {"message" : "Contacto eliminado exitosamente"}