from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from pyzbar import pyzbar
import base64
import uvicorn

app = FastAPI()

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def decode_barcode(image_data):
    # Converte base64 para imagem OpenCV
    img_bytes = base64.b64decode(image_data.split(',')[1])
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    # Converte para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Decodifica códigos de barras
    barcodes = pyzbar.decode(gray)
    
    if barcodes:
        barcode = barcodes[0]
        return {
            "type": barcode.type,
            "data": barcode.data.decode("utf-8")
        }
    return None

@app.post("/scan")
async def scan_barcode(data: dict):
    try:
        image_data = data.get("image")
        if not image_data:
            raise HTTPException(status_code=400, detail="Nenhuma imagem fornecida")
        
        result = decode_barcode(image_data)
        if result:
            return {
                "status": "success",
                "type": result["type"],
                "data": result["data"]
            }
        else:
            return {
                "status": "error",
                "message": "Nenhum código de barras encontrado"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)