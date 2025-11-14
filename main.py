from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import uvicorn
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from datetime import datetime
from typing import List

import uuid

class ConexionDB:
    def __init__(self, host, database, user, password, port=5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.conexion = None
        self.cursor = None
        print("🔌 Objeto de conexión creado")
        self.conectar()
 
    def conectar(self):
        try:
            self.conexion = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.cursor = self.conexion.cursor()
            print("✅ Conexión exitosa")
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
 
    def query(self, sql):
        if not self.conexion or not self.cursor:
            print("❌ No hay conexión activa")
            return None
        try:
            self.cursor.execute(sql)
            try:
                resultados = self.cursor.fetchall()
                print("✅ Consulta ejecutada exitosamente")
                return resultados
            except Exception as e:
                self.cursor.execute("COMMIT;")
                print("✅ Consulta ejecutada y cambios guardados")
                return None
        except Exception as e:
            print(f"❌ Error al ejecutar consulta: {e}")
            return None
 
    def cerrar(self):
        if self.cursor:
            self.cursor.close()
        if self.conexion:
            self.conexion.close()
        print("🔒 Conexión cerrada manualmente")
 
    def __str__(self):
        return f"ConexionDB(host={self.host}, database={self.database}, user={self.user}, port={self.port})"
 
    def __del__(self):
        print("💀 Destructor ejecutado: cerrando conexión automáticamente...")
        self.cerrar()
        
conexion = ConexionDB(
    host="localhost",
    database="redes",
    user="felatiko",
    password="felatiko"
)


class Usuario:
    def __init__(self, id, numero_telefono, contraseña, nombre, token=None, estado=True):
        self.id = id
        self.numero_telefono = numero_telefono
        self.contraseña = contraseña
        self.token = token
        self.estado = estado
        self.nombre = nombre
        
    def __str__(self):
        return f"Usuario(numero_telefono={self.numero_telefono}, estado={self.estado})"
    
    def validar_contraseña(self, contraseña):
        # Verifica si la contraseña es correcta usando la función de hash
        aux = check_password_hash(self.contraseña, contraseña)
        if aux:
            print("✅ Contraseña válida")
        else:
            print("❌ Contraseña inválida")
        return aux
    
    @staticmethod
    def buscar_usuario(numero_telefono):
        # Consulta la base de datos para encontrar un usuario por teléfono
        sql = f"SELECT id, numero_telefono, contraseña, token, estado, nombre FROM usuario WHERE numero_telefono = '{numero_telefono}' limit 1;"
        resultados = conexion.query(sql)
        if resultados and len(resultados) > 0:
            fila = resultados[0]
            usuario = Usuario(
                id=fila[0],
                numero_telefono=fila[1],
                contraseña=fila[2],
                nombre=fila[5],
                token=fila[3],
                estado=fila[4]
            )
            return usuario
            
        return None
    
    @staticmethod
    def buscar_usuario_por_token(token):
        # Consulta la base de datos para encontrar un usuario por token
        sql = f"SELECT id, numero_telefono, contraseña, token, estado, nombre FROM usuario WHERE token = '{token}' limit 1;"
        resultados = conexion.query(sql)
        if resultados and len(resultados) > 0:
            fila = resultados[0]
            usuario = Usuario(
                id=fila[0],
                numero_telefono=fila[1],
                contraseña=fila[2],
                token=fila[3],
                estado=fila[4],
                nombre=fila[5]
            )
            return usuario
            
        return None
    
    @staticmethod
    def hash_contraseña(contraseña):
        # Genera un hash seguro para la contraseña
        hashed = generate_password_hash(contraseña if contraseña else "")
        return hashed

# CREATE TABLE ubicacion (
#     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),               -- UUID propio para cada ubicación
#     latitud DOUBLE PRECISION NOT NULL,                            -- Latitud del punto
#     longitud DOUBLE PRECISION NOT NULL,                           -- Longitud del punto
#     fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    -- Fecha y hora en que se tomó la ubicación
#     usuario_id UUID REFERENCES usuario(id) ON DELETE CASCADE    -- Relación con la tabla usuario
# );

class Posicion:
    def __init__(self, latitud, longitud, usuario_id, id=None, fecha=None):
        self.id = id
        self.latitud = latitud
        self.longitud = longitud
        self.fecha = fecha
        self.usuario_id = usuario_id
        
    def __str__(self):
        return f"Posicion(latitud={self.latitud}, longitud={self.longitud}, usuario_id={self.usuario_id})"


app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
async def read_root():
    return "Hola mundo"

@app.post("/login")
async def login(request: dict):
    numero_telefono = request.get("numero_telefono")
    contraseña = request.get("contrasena")  # Asegúrate de que el campo sea 'contraseña'
    try:
        usuario = Usuario.buscar_usuario(numero_telefono)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al buscar usuario")
    
    if usuario and usuario.validar_contraseña(contraseña):
        return {"message": "Login exitoso", "token": usuario.token}
    else:
        raise HTTPException(status_code=401, detail="Número de teléfono o contraseña incorrectos")

@app.post("/register")
async def register(request: dict):
    numero_telefono = request.get("numero_telefono")
    contraseña = request.get("contrasena")  # Asegúrate de que el campo sea 'contraseña'
    # Verifica si el número de teléfono ya está registrado
    try:
        usuario_existente = Usuario.buscar_usuario(numero_telefono)
        raise HTTPException(status_code=400, detail="El número de teléfono ya está registrado")
    except Exception as e:
        pass
    # Crea el nuevo usuario y guarda la información

    nuevo_usuario = Usuario(
        id = None,
        numero_telefono=numero_telefono, 
        contraseña=contraseña, 
        nombre=request.get("nombre"),
        token=str(uuid.uuid4())  # Asegúrate de que el token esté en formato string
    )

    hashed_contraseña = Usuario.hash_contraseña(contraseña)
    sql = f"INSERT INTO usuario (numero_telefono, contraseña, token, estado) VALUES ('{nuevo_usuario.numero_telefono}', '{hashed_contraseña}', '{nuevo_usuario.token}', {nuevo_usuario.estado});"
    print(sql)
    conexion.query(sql)
        
    return {"message": "Usuario registrado exitosamente"}


@app.post("/guardar_posicion")
async def guardar_posicion(request: dict):
    latitud = request.get("latitud")
    longitud = request.get("longitud")
    usuario_id = request.get("usuario_token")
    usuario = Usuario.buscar_usuario_por_token(usuario_id)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token de usuario inválido")
    
    nueva_posicion = Posicion(
        latitud=latitud,
        longitud=longitud,
        usuario_id=usuario.id,
        fecha=datetime.now()
    )
    
    
    sql = """
    INSERT INTO ubicacion (latitud, longitud, fecha, usuario_id)
    VALUES ({}, {}, '{}', '{}');
    """.format(
        nueva_posicion.latitud,
        nueva_posicion.longitud,
        nueva_posicion.fecha,
        nueva_posicion.usuario_id
    )
    
    
    print(sql)
    conexion.query(sql)
    await manager.broadcast({"latitud": latitud, "longitud": longitud, "usuario_token": usuario_id}.__str__())
    
    return {"message": "Posición guardada exitosamente"}

@app.get("/usuarios")
async def obtener_usuarios():
    sql = "SELECT id,  nombre FROM usuario;"
    resultados = conexion.query(sql)
    usuarios = []
    if resultados:
        for fila in resultados:
            usuarios.append({
                "id": fila[0],
                "nombre": fila[1]
            })
    return JSONResponse(content=usuarios)


# Para gestionar las conexiones activas de WebSockets
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Instancia del manager
manager = WebSocketManager()

# Endpoint WebSocket para conectar
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("❌ WebSocket desconectado")

# Endpoint GET para disparar un mensaje en los WebSockets conectados
@app.get("/trigger_socket")
async def trigger_socket():
    message = "."
    await manager.broadcast(message)
    return ".Mensaje enviado a todos los WebSockets conectados."


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)