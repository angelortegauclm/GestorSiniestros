import os
import json
import psycopg2
import boto3

# Configuración
QUEUE_URL = os.environ.get("QUEUE_URL")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT"))
DB_NAME = os.environ.get("DB_NAME", "clase")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

sqs = boto3.client("sqs")

def lambda_handler(event, context):
    # Parsear body del POST
    try:
        body = json.loads(event.get("body", "{}"))
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Body inválido: {str(e)}"})
        }

    # Guardar en PostgreSQL
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        # Ejemplo: tabla "siniestros" con columnas id, cliente, vehiculo, poliza, reparacion
        cur.execute(
            """
            INSERT INTO siniestros (id, cliente, vehiculo, poliza, reparacion)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                body.get("id_siniestro"),
                json.dumps(body.get("cliente", {})),
                json.dumps(body.get("vehiculo", {})),
                json.dumps(body.get("poliza", {})),
                json.dumps(body.get("reparacion", {}))
            )
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"No se pudo guardar en DB: {str(e)}"})
        }

    # Enviar mensaje a SQS
    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(body)
        )
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"No se pudo enviar a SQS: {str(e)}"})
        }

    # Respuesta HTTP
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Datos recibidos, guardados en DB y enviados a SQS"})
    }