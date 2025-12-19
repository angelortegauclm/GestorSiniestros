import boto3
import os
import json
import uuid
from datetime import datetime

# Configuración Global
BUCKET_NAME = os.environ.get('INVOICE_BUCKET_NAME')
IVA_PORCENTAJE = 0.21
s3 = boto3.client('s3')

def lambda_handler(event, context):
    print("--- INICIANDO PROCESO DE FACTURACIÓN COMPLETO ---")
    print("Datos recibidos:", json.dumps(event))

    try:
        # ====================================================
        # 1. EXTRACCIÓN DE DATOS 
        # ====================================================
        siniestro_id = event.get('id_siniestro', 'UNK-000')
        cliente = event.get('cliente', {})
        vehiculo = event.get('vehiculo', {})
        poliza = event.get('poliza', {})
        reparacion = event.get('reparacion', {})

        # ====================================================
        # 2. CÁLCULOS BASE Y DEPRECIACIÓN
        # ====================================================
        mano_obra = float(reparacion.get('coste_mano_obra', 0))
        piezas = float(reparacion.get('coste_piezas', 0))
        
        # Validación básica
        if mano_obra < 0 or piezas < 0:
            raise ValueError("Los costes no pueden ser negativos.")

        # Lógica de Antigüedad
        anio_coche = int(vehiculo.get('anio_matriculacion', datetime.now().year))
        antiguedad = datetime.now().year - anio_coche
        
        depreciacion_piezas = 0.0
        mensaje_vehiculo = "Vehículo moderno (<10 años). Sin depreciación."

        # REGLA 1: Si tiene más de 10 años, depreciamos piezas un 20%
        if antiguedad > 10:
            depreciacion_piezas = piezas * 0.20
            mensaje_vehiculo = f"Vehículo antiguo ({antiguedad} años). Depreciación del 20% aplicada."

        # Costes ajustados
        piezas_final = piezas - depreciacion_piezas
        base_imponible = mano_obra + piezas_final
        impuestos = base_imponible * IVA_PORCENTAJE
        total_reparacion = base_imponible + impuestos

        # ====================================================
        # 3. LÓGICA DE NEGOCIO SEGÚN TIPO DE SEGURO
        # ====================================================
        tipo_seguro = poliza.get('tipo', 'TERCEROS').upper()
        franquicia = float(poliza.get('franquicia', 0))
        limite = float(poliza.get('limite_cobertura', 0))

        pago_aseguradora = 0.0
        pago_cliente = 0.0
        nota_resolucion = ""

        # CASO A: TERCEROS (Daños propios NO cubiertos)
        if tipo_seguro == 'TERCEROS':
            pago_aseguradora = 0.0
            pago_cliente = total_reparacion
            nota_resolucion = "Póliza a TERCEROS: No cubre daños propios del vehículo asegurado."

        # CASO B: TODO RIESGO (Cobertura total, cliente paga 0 salvo límite)
        elif tipo_seguro == 'TODO_RIESGO':
            pago_cliente = 0.0
            if total_reparacion > limite:
                pago_aseguradora = limite
                pago_cliente = total_reparacion - limite
                nota_resolucion = "TODO RIESGO: Cubierto hasta el límite de la póliza."
            else:
                pago_aseguradora = total_reparacion
                nota_resolucion = "TODO RIESGO: Cobertura completa aplicada."

        # CASO C: TODO RIESGO CON FRANQUICIA (Cliente paga la franquicia)
        elif 'FRANQUICIA' in tipo_seguro:
            if total_reparacion <= franquicia:
                pago_cliente = total_reparacion
                pago_aseguradora = 0.0
                nota_resolucion = f"El coste ({total_reparacion:.2f}€) es inferior a la franquicia ({franquicia}€)."
            else:
                pago_cliente = franquicia
                resto = total_reparacion - franquicia
                
                # Verificar límite sobre el resto
                if resto > limite:
                    pago_aseguradora = limite
                    pago_cliente += (resto - limite)
                else:
                    pago_aseguradora = resto
                
                nota_resolucion = f"Aplicada franquicia de {franquicia}€. El seguro cubre el resto."
        
        else:
            # Fallback de seguridad
            pago_cliente = total_reparacion
            nota_resolucion = f"Tipo de seguro '{tipo_seguro}' desconocido. Se rechaza cobertura por defecto."

        # ====================================================
        # 4. GENERACIÓN DE FACTURA (FORMATO DETALLADO)
        # ====================================================
        fecha_emision = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nombre_archivo = f"Factura_{vehiculo.get('matricula', 'SIN-MAT')}_{siniestro_id}.pdf"

        contenido_factura = f"""
        ================================================================
                           FACTURA DE SINIESTRO
                           Gestor Siniestros Systems
        ================================================================
        ID Siniestro:   {siniestro_id}
        Fecha Emisión:  {fecha_emision}
        
        DATOS DEL ASEGURADO
        -------------------
        Cliente:        {cliente.get('nombre', 'N/A')}
        DNI/NIF:        {cliente.get('dni', 'N/A')}
        Email:          {cliente.get('email', 'N/A')}
        
        DATOS DEL VEHÍCULO
        ------------------
        Matrícula:      {vehiculo.get('matricula', 'N/A')}
        Modelo:         {vehiculo.get('marca', '')} {vehiculo.get('modelo', '')}
        Antigüedad:     {antiguedad} años (Matriculado en {anio_coche})
        
        DETALLE DE LA REPARACIÓN
        ------------------------
        Taller:         {reparacion.get('taller', 'N/A')}
        
        (+) Mano de Obra:        {mano_obra:10.2f} EUR
        (+) Piezas (PVP):        {piezas:10.2f} EUR
        (-) Depreciación Piezas: {depreciacion_piezas:10.2f} EUR
            * {mensaje_vehiculo}
        ----------------------------------------
        BASE IMPONIBLE:          {base_imponible:10.2f} EUR
        (+) IVA ({int(IVA_PORCENTAJE*100)}%):          {impuestos:10.2f} EUR
        ----------------------------------------
        TOTAL SINIESTRO:         {total_reparacion:10.2f} EUR
        ========================================

        RESOLUCIÓN DE COBERTURA
        -----------------------
        Tipo Póliza:    {tipo_seguro}
        Franquicia:     {franquicia:.2f} EUR
        Límite Máx.:    {limite:.2f} EUR
        
        MOTIVO:
        {nota_resolucion}
        
        ========================================
        >> A PAGAR POR ASEGURADORA:  {pago_aseguradora:10.2f} EUR
        >> A PAGAR POR CLIENTE:      {pago_cliente:10.2f} EUR
        ========================================
        """

        # ====================================================
        # 5. SUBIDA A S3
        # ====================================================
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=nombre_archivo,
            Body=contenido_factura,
            ContentType='application/pdf'
        )
        
        print(f"Factura generada exitosamente: {nombre_archivo}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensaje': 'Proceso completado',
                'archivo': nombre_archivo,
                'resumen_financiero': {
                    'total': total_reparacion,
                    'pago_cliente': pago_cliente,
                    'pago_seguro': pago_aseguradora
                }
            })
        }

    except Exception as e:
        print(f"ERROR CRÍTICO: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}