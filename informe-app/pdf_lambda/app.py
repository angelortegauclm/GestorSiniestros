import json
import boto3
from reportlab.pdfgen import canvas
import uuid
import os

s3 = boto3.client('s3')
BUCKET = "mi-bucket-sam-deploy-jmrg1234"  # cambiar por tu bucket real

def lambda_handler(event, context):
    # EventBridge envía los detalles en event['detail'] ya como dict
    detalle = event['detail']
    nombre = detalle.get('nombre', 'SinNombre')
    
    # Generar PDF temporal
    file_name = f"informe-{uuid.uuid4()}.pdf"
    file_path = f"/tmp/{file_name}"
    
    c = canvas.Canvas(file_path)
    c.drawString(100, 750, f"Informe para: {nombre}")
    c.save()
    
    # Subir a S3
    s3.upload_file(file_path, BUCKET, file_name)
    
    return {
        "statusCode": 200,
        "body": json.dumps({"mensaje": f"PDF generado y subido como {file_name}"})
    }

