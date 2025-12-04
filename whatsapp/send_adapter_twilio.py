import os
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)

# Descomentar cuando instales twilio:
# from twilio.rest import Client


def send_message_twilio(
    phone: str,
    text: str,
    attachments: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """
    Adapter real para Twilio.
    
    Configuración requerida en .env:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_FROM
    
    Args:
        phone: Número de teléfono destino en formato internacional (+593...)
        text: Contenido del mensaje
        attachments: Lista de URLs de archivos adjuntos (opcional)
        
    Returns:
        (success: bool, message_id_or_error: str)
        
    Uso:
        En whatsapp/send_adapter.py, reemplaza la función send_message:
        from .send_adapter_twilio import send_message_twilio as send_message
    """
    try:
        # Obtener credenciales del entorno
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_FROM')
        
        if not all([account_sid, auth_token, from_number]):
            raise ValueError(
                "Faltan credenciales de Twilio en .env: "
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM"
            )
        
        # Descomentar cuando instales twilio (pip install twilio):
        # client = Client(account_sid, auth_token)
        # 
        # # Preparar parámetros del mensaje
        # msg_params = {
        #     'body': text,
        #     'from_': from_number,
        #     'to': phone
        # }
        # 
        # # Añadir attachments si existen
        # if attachments:
        #     msg_params['media_url'] = attachments
        # 
        # # Enviar mensaje
        # message = client.messages.create(**msg_params)
        # 
        # logger.info(
        #     f"[Twilio] Mensaje enviado a {phone}: "
        #     f"SID={message.sid}, Status={message.status}"
        # )
        # 
        # return True, message.sid
        
        # Por ahora, retornar error porque twilio no está instalado
        raise NotImplementedError(
            "Twilio no está configurado. "
            "Instala 'pip install twilio' y descomenta el código en send_adapter_twilio.py"
        )
        
    except Exception as e:
        logger.error(f"[Twilio] Error enviando a {phone}: {str(e)}")
        return False, str(e)


def send_message_360dialog(
    phone: str,
    text: str,
    attachments: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """
    Adapter alternativo para 360dialog (WhatsApp Business API).
    
    Configuración requerida en .env:
    - DIALOG360_API_KEY
    - DIALOG360_NAMESPACE
    
    Args:
        phone: Número de teléfono destino en formato internacional
        text: Contenido del mensaje
        attachments: Lista de URLs de archivos adjuntos (opcional)
        
    Returns:
        (success: bool, message_id_or_error: str)
    """
    try:
        api_key = os.getenv('DIALOG360_API_KEY')
        namespace = os.getenv('DIALOG360_NAMESPACE')
        
        if not all([api_key, namespace]):
            raise ValueError(
                "Faltan credenciales de 360dialog en .env: "
                "DIALOG360_API_KEY, DIALOG360_NAMESPACE"
            )
        
        # Implementar llamada a 360dialog API aquí
        # Ver: https://docs.360dialog.com/
        
        raise NotImplementedError(
            "360dialog no está implementado aún. "
            "Consulta la documentación en https://docs.360dialog.com/"
        )
        
    except Exception as e:
        logger.error(f"[360dialog] Error enviando a {phone}: {str(e)}")
        return False, str(e)
