from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import logging


conn = sqlite3.connect("contactos.db")
app = FastAPI()


# TO DO: Cambiar el origen de acuerdo a la URL del frontend
origins = [
    "http://127.0.0.1:5000",
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


@app.get("/")
async def root():
    return {"message": "/contactos para obtener todos los contactos"}

@app.get("/contactos")
async def obtener_contactos():
    c = conn.cursor()
    c.execute('SELECT * FROM contactos;')
    response = []
    for row in c:
        contacto = {"email":row[0],"nombre":row[1], "telefono":row[2]}
        response.append(contacto)
    return response


@app.post("/contactos")
async def crear_contacto(contacto: Contacto):
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
async def obtener_contacto(email: str):
    c = conn.cursor()
    c.execute('SELECT * FROM contactos WHERE email = ?', (email,))
    contacto = None
    for row in c:
        contacto = {"email":row[0],"nombre":row[1],"telefono":row[2]}
    if contacto is None:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    return contacto


@app.put("/contactos/{email}")
async def actualizar_contacto(email: str, contacto: Contacto):
    c = conn.cursor()
    c.execute('UPDATE contactos SET nombre = ?, telefono = ? WHERE email = ?',
              (contacto.nombre, contacto.telefono, email))
    conn.commit()
    return contacto

@app.delete("/contactos/{email}")
async def eliminar_contacto(email: str):
    c = conn.cursor()
    c.execute('DELETE FROM contactos WHERE email = ?', (email,))
    conn.commit()
    return {"message" : "Contacto eliminado exitosamente"}