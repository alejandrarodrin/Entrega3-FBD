from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB")

if not MONGO_URI:
    raise Exception("Falta la variable MONGO_URI")

if not MONGO_DB:
    raise Exception("Falta la variable MONGO_DB")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# Colecciones
usuarios_collection = db["usuarios"]
hoteles_collection = db["hoteles"]
resenas_collection = db["resenas"]


def convertir_documento(documento):
    if documento is None:
        return None

    doc = dict(documento)

    if "_id" in doc:
        doc["_id"] = str(doc["_id"])

    if "fecha" in doc and hasattr(doc["fecha"], "isoformat"):
        doc["fecha"] = doc["fecha"].isoformat()

    if "fecha_actualizacion" in doc and hasattr(doc["fecha_actualizacion"], "isoformat"):
        doc["fecha_actualizacion"] = doc["fecha_actualizacion"].isoformat()

    if "respuesta_admin" in doc and isinstance(doc["respuesta_admin"], dict):
        respuesta = dict(doc["respuesta_admin"])

        if "fecha_respuesta" in respuesta and hasattr(respuesta["fecha_respuesta"], "isoformat"):
            respuesta["fecha_respuesta"] = respuesta["fecha_respuesta"].isoformat()

        doc["respuesta_admin"] = respuesta

    return doc


@app.get("/")
def home():
    return {
        "estado": "API funcionando correctamente",
        "base_de_datos": MONGO_DB,
        "rutas": [
            "/usuarios",
            "/hoteles",
            "/resenas",
            "/resenas/publicadas",
            "/resenas/destacadas",
            "/resenas/hotel/{hotel_id}",
            "/resenas/ciudad/{ciudad}",
            "/resenas/calificacion/{calificacion}"
        ]
    }




@app.get("/usuarios")
def get_usuarios():
    usuarios = list(usuarios_collection.find())
    return [convertir_documento(usuario) for usuario in usuarios]


@app.get("/usuarios/{usuario_id}")
def get_usuario_por_id(usuario_id: int):
    usuario = usuarios_collection.find_one({"_id": usuario_id})

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return convertir_documento(usuario)



@app.get("/hoteles")
def get_hoteles():
    hoteles = list(hoteles_collection.find())
    return [convertir_documento(hotel) for hotel in hoteles]


@app.get("/hoteles/{hotel_id}")
def get_hotel_por_id(hotel_id: int):
    hotel = hoteles_collection.find_one({"_id": hotel_id})

    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel no encontrado")

    return convertir_documento(hotel)


@app.get("/hoteles/ciudad/{ciudad}")
def get_hoteles_por_ciudad(ciudad: str):
    hoteles = list(hoteles_collection.find({"ciudad": ciudad}))
    return [convertir_documento(hotel) for hotel in hoteles]



@app.get("/resenas-apex")
def get_resenas_apex():
    resenas = list(resenas_collection.find())

    resultado = []

    for r in resenas:
        respuesta_admin = r.get("respuesta_admin", {})

        resultado.append({
            "id": str(r.get("_id")),
            "hotel_id": r.get("hotel_id"),
            "ciudad_hotel": r.get("ciudad_hotel"),
            "cliente_id": r.get("cliente_id"),
            "reserva_id": r.get("reserva_id"),
            "fecha": r.get("fecha").isoformat() if r.get("fecha") else None,
            "calificacion": r.get("calificacion"),
            "comentario": r.get("comentario"),
            "estado": r.get("estado"),
            "destacada": r.get("destacada"),
            "votos_utilidad": r.get("votos_utilidad"),
            "admin_id": respuesta_admin.get("admin_id"),
            "respuesta_admin": respuesta_admin.get("respuesta"),
            "fecha_respuesta": respuesta_admin.get("fecha_respuesta").isoformat()
                if respuesta_admin.get("fecha_respuesta") else None
        })

    return resultado

@app.get("/resenas")
def get_resenas():
    try:
        resenas = list(resenas_collection.find())
        return [convertir_documento(resena) for resena in resenas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resenas/publicadas")
def get_resenas_publicadas():
    resenas = list(resenas_collection.find({"estado": "publicada"}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/eliminadas")
def get_resenas_eliminadas():
    resenas = list(resenas_collection.find({"estado": "eliminada"}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/destacadas")
def get_resenas_destacadas():
    resenas = list(resenas_collection.find({"destacada": True}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/hotel/{hotel_id}")
def get_resenas_por_hotel(hotel_id: int):
    resenas = list(resenas_collection.find({"hotel_id": hotel_id}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/ciudad/{ciudad}")
def get_resenas_por_ciudad(ciudad: str):
    resenas = list(resenas_collection.find({"ciudad_hotel": ciudad}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/calificacion/{calificacion}")
def get_resenas_por_calificacion(calificacion: int):
    if calificacion < 1 or calificacion > 5:
        raise HTTPException(
            status_code=400,
            detail="La calificación debe estar entre 1 y 5"
        )

    resenas = list(resenas_collection.find({"calificacion": calificacion}))
    return [convertir_documento(resena) for resena in resenas]


@app.get("/resenas/cliente/{cliente_id}")
def get_resenas_por_cliente(cliente_id: int):
    resenas = list(resenas_collection.find({"cliente_id": cliente_id}))
    return [convertir_documento(resena) for resena in resenas]


@app.post("/resenas")
def crear_resena(resena: dict):
    try:
        # Convertir fecha string a datetime para MongoDB
        if "fecha" in resena and isinstance(resena["fecha"], str):
            resena["fecha"] = datetime.fromisoformat(
                resena["fecha"].replace("Z", "+00:00")
            )

        resena.setdefault("estado", "publicada")
        resena.setdefault("destacada", False)
        resena.setdefault("votos_utilidad", 0)

        if "calificacion" not in resena or not (1 <= int(resena["calificacion"]) <= 5):
            raise HTTPException(status_code=400, detail="La calificación debe estar entre 1 y 5")

        if resenas_collection.find_one({"reserva_id": resena["reserva_id"]}):
            raise HTTPException(status_code=400, detail="Esa reserva ya tiene una reseña")

        resultado = resenas_collection.insert_one(resena)

        nueva_resena = resenas_collection.find_one({
            "_id": resultado.inserted_id
        })

        return convertir_documento(nueva_resena)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/resenas/{resena_id}")
def actualizar_resena(resena_id: str, datos_actualizados: dict):
    try:
        object_id = ObjectId(resena_id)
    except:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    resultado = resenas_collection.update_one(
        {"_id": object_id},
        {"$set": datos_actualizados}
    )

    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    resena_actualizada = resenas_collection.find_one({"_id": object_id})
    return convertir_documento(resena_actualizada)


@app.delete("/resenas/{resena_id}")
def eliminar_resena(resena_id: str):
    try:
        object_id = ObjectId(resena_id)
    except:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    resultado = resenas_collection.delete_one({"_id": object_id})

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    return {
        "estado": "Reseña eliminada correctamente",
        "id": resena_id
    }

@app.put("/resenas/{resena_id}/util")
def marcar_resena_util(resena_id: str):
    try:
        object_id = ObjectId(resena_id)
    except:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    resultado = resenas_collection.update_one(
        {"_id": object_id},
        {"$inc": {"votos_utilidad": 1}}
    )

    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    resena_actualizada = resenas_collection.find_one({"_id": object_id})
    return convertir_documento(resena_actualizada)


@app.put("/resenas/{resena_id}/destacar")
def destacar_resena(resena_id: str):
    try:
        object_id = ObjectId(resena_id)
    except:
        raise HTTPException(status_code=400, detail="ID de reseña inválido")

    resena = resenas_collection.find_one({"_id": object_id})

    if not resena:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    hotel_id = resena.get("hotel_id")

    resenas_collection.update_many(
        {"hotel_id": hotel_id},
        {"$set": {"destacada": False}}
    )

    resenas_collection.update_one(
        {"_id": object_id},
        {"$set": {"destacada": True}}
    )

    resena_actualizada = resenas_collection.find_one({"_id": object_id})
    return convertir_documento(resena_actualizada)


@app.get("/rfc/top-hoteles")
def rfc_top_hoteles(fecha_inicio: str = "2026-01-01", fecha_fin: str = "2026-12-31"):
    try:
        inicio = datetime.fromisoformat(fecha_inicio)
        fin = datetime.fromisoformat(fecha_fin)

        pipeline = [
            {
                "$match": {
                    "estado": "publicada",
                    "fecha": {
                        "$gte": inicio,
                        "$lte": fin
                    }
                }
            },
            {
                "$group": {
                    "_id": "$hotel_id",
                    "ciudad_hotel": { "$first": "$ciudad_hotel" },
                    "promedio_calificacion": { "$avg": "$calificacion" },
                    "total_resenas": { "$sum": 1 }
                }
            },
            {
                "$sort": {
                    "promedio_calificacion": -1,
                    "total_resenas": -1
                }
            },
            {
                "$limit": 10
            },
            {
                "$project": {
                    "_id": 0,
                    "hotel_id": "$_id",
                    "ciudad_hotel": 1,
                    "promedio_calificacion": { "$round": ["$promedio_calificacion", 2] },
                    "total_resenas": 1
                }
            }
        ]

        return list(resenas_collection.aggregate(pipeline))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rfc/evolucion-hotel/{hotel_id}")
def rfc_evolucion_hotel(hotel_id: int, anio: int = 2026):
    try:
        inicio = datetime(anio, 1, 1)
        fin = datetime(anio, 12, 31, 23, 59, 59)

        pipeline = [
            {
                "$match": {
                    "hotel_id": hotel_id,
                    "estado": "publicada",
                    "fecha": {
                        "$gte": inicio,
                        "$lte": fin
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "anio": { "$year": "$fecha" },
                        "mes": { "$month": "$fecha" }
                    },
                    "promedio_calificacion": { "$avg": "$calificacion" },
                    "total_resenas": { "$sum": 1 }
                }
            },
            {
                "$sort": {
                    "_id.anio": 1,
                    "_id.mes": 1
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "anio": "$_id.anio",
                    "mes": "$_id.mes",
                    "promedio_calificacion": { "$round": ["$promedio_calificacion", 2] },
                    "total_resenas": 1
                }
            }
        ]

        return list(resenas_collection.aggregate(pipeline))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rfc/comparativo-ciudad/{ciudad}")
def rfc_comparativo_ciudad(ciudad: str):
    try:
        pipeline = [
            {
                "$match": {
                    "ciudad_hotel": ciudad,
                    "estado": "publicada"
                }
            },
            {
                "$group": {
                    "_id": "$hotel_id",
                    "promedio_calificacion": { "$avg": "$calificacion" },
                    "total_resenas": { "$sum": 1 },
                    "resenas_con_respuesta": {
                        "$sum": {
                            "$cond": [
                                { "$ifNull": ["$respuesta_admin", False] },
                                1,
                                0
                            ]
                        }
                    },
                    "resenas_destacadas": {
                        "$sum": {
                            "$cond": ["$destacada", 1, 0]
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "porcentaje_respuesta_admin": {
                        "$multiply": [
                            { "$divide": ["$resenas_con_respuesta", "$total_resenas"] },
                            100
                        ]
                    },
                    "porcentaje_destacadas": {
                        "$multiply": [
                            { "$divide": ["$resenas_destacadas", "$total_resenas"] },
                            100
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "hoteles": { "$push": "$$ROOT" },
                    "promedio_ciudad": { "$avg": "$promedio_calificacion" }
                }
            },
            {
                "$unwind": "$hoteles"
            },
            {
                "$project": {
                    "_id": 0,
                    "hotel_id": "$hoteles._id",
                    "promedio_calificacion": { "$round": ["$hoteles.promedio_calificacion", 2] },
                    "total_resenas": "$hoteles.total_resenas",
                    "porcentaje_respuesta_admin": { "$round": ["$hoteles.porcentaje_respuesta_admin", 2] },
                    "porcentaje_destacadas": { "$round": ["$hoteles.porcentaje_destacadas", 2] },
                    "promedio_ciudad": { "$round": ["$promedio_ciudad", 2] },
                    "por_debajo_promedio_ciudad": {
                        "$lt": ["$hoteles.promedio_calificacion", "$promedio_ciudad"]
                    }
                }
            },
            {
                "$sort": {
                    "promedio_calificacion": -1
                }
            }
        ]

        return list(resenas_collection.aggregate(pipeline))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))