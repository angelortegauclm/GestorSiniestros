import json
import boto3

# Cliente de EventBridge
eventbridge = boto3.client('events')

def lambda_handler(event, context):
    # Parsear el body JSON
    body = json.loads(event.get('body', '{}'))

    # Publicar evento en EventBridge
    response = eventbridge.put_events(
        Entries=[{
            'Source': 'app.informes',
            'DetailType': 'InformeSolicitado',
            'Detail': json.dumps(body)
        }]
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "mensaje": "Informe enviado a procesar",
            "event_response": response
        })
    }
