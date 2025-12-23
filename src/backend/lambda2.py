import boto3
import os
import json
from datetime import datetime
#import psycopg2  # librería para Conectarte a PostgreSQL y ejecutar SQL

# Configuración de Clientes AWS
sqs = boto3.client('sqs')

# Configuración Global
QUEUE_2_URL = os.environ.get('QUEUE_2_URL')
IVA_PORCENTAJE = 0.21


# Variables de entorno de la DB
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASSWORD')
QUEUE_2_URL = os.environ.get('QUEUE_2_URL')


def lambda_handler(event, context):
    print("--- INICIANDO CÁLCULO DE COSTES ---")
    
    # 1. PROCESAMIENTO DE MENSAJES DESDE SQS (Queue1)
    for record in event.get('Records', []):
        try:
            # SQS entrega los datos en 'body' como string
            data = json.loads(record.get('body', '{}'))
            
            # EXTRACCIÓN DE DATOS
            siniestro_id = data.get('id_siniestro', 'UNK-000')
            cliente = data.get('cliente', {})
            vehiculo = data.get('vehiculo', {})
            poliza = data.get('poliza', {})
            reparacion = data.get('reparacion', {})

            # 2. CÁLCULOS DE DEPRECIACIÓN POR ANTIGÜEDAD
            mano_obra = float(reparacion.get('coste_mano_obra', 0))
            piezas = float(reparacion.get('coste_piezas', 0))
            
            anio_coche = int(vehiculo.get('anio_matriculacion', datetime.now().year))
            antiguedad = datetime.now().year - anio_coche
            
            depreciacion_piezas = 0.0
            if antiguedad > 10:
                depreciacion_piezas = piezas * 0.20

            piezas_final = piezas - depreciacion_piezas
            base_imponible = mano_obra + piezas_final
            impuestos = base_imponible * IVA_PORCENTAJE
            total_reparacion = base_imponible + impuestos

            # 3. LÓGICA DE SEGURO (TERCEROS / TODO RIESGO / FRANQUICIA)
            tipo_seguro = poliza.get('tipo', 'TERCEROS').upper()
            franquicia = float(poliza.get('franquicia', 0))
            limite = float(poliza.get('limite_cobertura', 0))

            pago_aseguradora = 0.0
            pago_cliente = 0.0

            if tipo_seguro == 'TERCEROS':
                pago_cliente = total_reparacion
            elif tipo_seguro == 'TODO_RIESGO':
                if total_reparacion > limite:
                    pago_aseguradora = limite
                    pago_cliente = total_reparacion - limite
                else:
                    pago_aseguradora = total_reparacion
            elif 'FRANQUICIA' in tipo_seguro:
                if total_reparacion <= franquicia:
                    pago_cliente = total_reparacion
                else:
                    pago_cliente = franquicia
                    resto = total_reparacion - franquicia
                    if resto > limite:
                        pago_aseguradora = limite
                        pago_cliente += (resto - limite)
                    else:
                        pago_aseguradora = resto


            #  4. GUARDAR RESULTADOS EN LA BASE DE DATOS
            # try:
            #     conn = psycopg2.connect(
            #         host=DB_HOST,
            #         database=DB_NAME,
            #         user=DB_USER,
            #         password=DB_PASS
            #     )
            #     cur = conn.cursor()
                
                # Actualiza el registro que creó la Lambda 1
            #     cur.execute(
            #         """
            #         UPDATE table_siniestros 
            #         SET total_coste = %s, pago_seguro = %s, pago_cliente = %s
            #         WHERE id = %s
            #         """,
            #         (
            #             round(total_reparacion, 2),
            #             round(pago_aseguradora, 2),
            #             round(pago_cliente, 2),
            #             siniestro_id
            #         )
            #     )
                
            #     conn.commit()
            #     cur.close()
            #     conn.close()
            #     print(f"Base de datos actualizada para siniestro: {siniestro_id}")
            # except Exception as db_e:
            #     print(f"Error al escribir en DB: {str(db_e)}")
                # No lanzamos el error para que al menos intente enviar el mensaje a SQS


            # 5. PREPARAR DATOS (PDF/Email)
            resultado_calculo = {
                "id_siniestro": siniestro_id,
                "datos_cliente": cliente,
                "datos_vehiculo": vehiculo,
                "detalle_economico": {
                    "base_imponible": round(base_imponible, 2),
                    "iva": round(impuestos, 2),
                    "total_siniestro": round(total_reparacion, 2),
                    "pago_aseguradora": round(pago_aseguradora, 2),
                    "pago_cliente": round(pago_cliente, 2),
                    "antiguedad_aplicada": antiguedad
                }
            }

            # 6. ENVIAR A LA SIGUIENTE COLA (Queue2)
            sqs.send_message(
                QueueUrl=QUEUE_2_URL,
                MessageBody=json.dumps(resultado_calculo)
            )
            print(f"Cálculo enviado a Queue2 para siniestro: {siniestro_id}")

        except Exception as e:
            print(f"Error procesando record: {str(e)}")
            continue

    return {'statusCode': 200, 'body': 'Cálculos completados y enviados'}