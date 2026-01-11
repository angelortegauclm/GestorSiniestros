import boto3
import os
import json
 
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
sns_client = boto3.client('sns')
s3_client = boto3.client('s3')
 
def lambda_handler(event, context):
    print("--- INICIANDO NOTIFICACIÓN DE FACTURA ---")
    try:
        if not SNS_TOPIC_ARN:
            print("ERROR: Variable de entorno SNS_TOPIC_ARN no configurada.")
            return {'statusCode': 500, 'body': json.dumps('Configuración de SNS faltante')}
    
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        file_key = record['s3']['object']['key']
    
        presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': file_key},
                ExpiresIn=86400
            )
    
        siniestro_id = file_key.replace('factura_', '').replace('.pdf', '')
    
        message_text = (
                f"Estimado cliente,\n\n"
                f"Le informamos que el informe de tasación para el siniestro '{siniestro_id}' "
                f"ya ha sido generado y está listo para su descarga.\n\n"
                f"ACCESO AL DOCUMENTO:\n"
                f"{presigned_url}\n\n"
                f"IMPORTANTE: Por motivos de seguridad, este enlace expirará en 24 horas.\n\n"
                f"Atentamente,\n"
                f"El equipo de Gestión de Siniestros\n"
            )
   
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message_text,
            Subject='Nueva Factura Disponible'
        )
        print("Notificación de factura enviada con éxito")
    except Exception as e:
        print(f"ERROR al publicar en SNS: {e}")
        return {'statusCode': 500, 'body': json.dumps('Fallo al enviar notificación')}
       
    return {
        'statusCode': 200,
        'body': json.dumps('Proceso de notificación de factura terminado.')
    }