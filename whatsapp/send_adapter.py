import time
import logging
import os
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuración del servicio WhatsApp Web.js
WHATSAPP_SERVICE_URL = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:3000')
USE_REAL_WHATSAPP = os.getenv('USE_REAL_WHATSAPP', 'false').lower() == 'true'

def send_message(phone, text, attachment_path=None, attachment_type=None):
    """
    Adapter para envío de mensajes vía WhatsApp Web.js o simulado.
    
    Args:
        phone: Número de teléfono (formato: +593987654321)
        text: Texto del mensaje
        attachment_path: Ruta al archivo adjunto (opcional)
        attachment_type: Tipo de adjunto: image, video, audio, document (opcional)
    
    Returns:
        (success: bool, info: str)
    """
    if USE_REAL_WHATSAPP:
        return _send_via_whatsapp_webjs(phone, text, attachment_path, attachment_type)
    else:
        return _send_simulated(phone, text, attachment_path, attachment_type)

def _send_simulated(phone, text, attachment_path=None, attachment_type=None):
    """Simulación de envío (desarrollo/testing)"""
    try:
        time.sleep(0.5)
        
        attachment_info = ""
        if attachment_path:
            attachment_info = f" + {attachment_type or 'file'}: {attachment_path}"
        
        logger.info(f"[Adapter] Simulado: {phone} -> {text[:80]}{attachment_info}")
        return True, "simulated"
    except Exception as e:
        return False, str(e)

def _send_via_whatsapp_webjs(phone, text, attachment_path=None, attachment_type=None):
    """Envío real vía WhatsApp Web.js"""
    try:
        # Limpiar formato de teléfono (quitar + y espacios)
        clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
        
        if attachment_path:
            # Enviar con archivo adjunto
            url = f"{WHATSAPP_SERVICE_URL}/send-media"
            
            # Convertir ruta relativa a absoluta
            if not os.path.isabs(attachment_path):
                attachment_path = os.path.join(settings.MEDIA_ROOT, attachment_path)
            
            payload = {
                'phone': clean_phone,
                'message': text,
                'mediaPath': attachment_path,
                'mediaType': attachment_type
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
        else:
            # Enviar solo texto
            url = f"{WHATSAPP_SERVICE_URL}/send"
            payload = {
                'phone': clean_phone,
                'message': text
            }
            
            response = requests.post(url, json=payload, timeout=15)
        
        # Verificar respuesta
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                message_id = data.get('messageId', 'unknown')
                logger.info(f"[WhatsApp] ✓ Enviado a {phone}: {text[:60]}...")
                return True, message_id
            else:
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"[WhatsApp] ✗ Error: {error_msg}")
                return False, error_msg
        
        elif response.status_code == 503:
            error_msg = "WhatsApp no está conectado. Escanea el QR code."
            logger.warning(f"[WhatsApp] ⚠ {error_msg}")
            return False, error_msg
        
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"[WhatsApp] ✗ {error_msg}")
            return False, error_msg
            
    except requests.exceptions.ConnectionError:
        error_msg = f"No se pudo conectar al servicio WhatsApp en {WHATSAPP_SERVICE_URL}"
        logger.error(f"[WhatsApp] ✗ {error_msg}")
        return False, error_msg
        
    except requests.exceptions.Timeout:
        error_msg = "Timeout al enviar mensaje a WhatsApp"
        logger.error(f"[WhatsApp] ✗ {error_msg}")
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        logger.error(f"[WhatsApp] ✗ {error_msg}")
        return False, error_msg

def check_whatsapp_status():
    """Verificar si el servicio WhatsApp está conectado y listo"""
    try:
        # Primero verificar salud del servicio
        response = requests.get(f"{WHATSAPP_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status_info = {
                'connected': data.get('status') == 'ready',
                'status': data.get('status'),
                'timestamp': data.get('timestamp'),
                'qr': None
            }
            
            # Si no está conectado, intentar obtener QR
            if data.get('status') != 'ready':
                try:
                    qr_response = requests.get(f"{WHATSAPP_SERVICE_URL}/qr", timeout=5)
                    if qr_response.status_code == 200:
                        qr_data = qr_response.json()
                        if qr_data.get('qr'):
                            status_info['qr'] = qr_data['qr']
                except:
                    pass
            
            return status_info
    except:
        pass
    
    return {
        'connected': False,
        'status': 'disconnected',
        'qr': None
    }

def get_qr_code():
    """Obtener QR code para autenticación"""
    try:
        response = requests.get(f"{WHATSAPP_SERVICE_URL}/qr", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

# Ejemplo (comentado) para WhatsApp API con adjuntos:
# from whatsapp_api_client import Client
# def send_message_whatsapp(phone, text, attachment_path=None, attachment_type=None):
#     client = Client(API_KEY)
#     
#     if attachment_path:
#         # Enviar con adjunto
#         if attachment_type == 'image':
#             response = client.send_image(phone, attachment_path, caption=text)
#         elif attachment_type == 'video':
#             response = client.send_video(phone, attachment_path, caption=text)
#         elif attachment_type == 'audio':
#             response = client.send_audio(phone, attachment_path)
#         elif attachment_type == 'document':
#             response = client.send_document(phone, attachment_path, caption=text)
#         else:
#             response = client.send_file(phone, attachment_path)
#     else:
#         # Mensaje de texto simple
#         response = client.send_message(phone, text)
#     
#     return True, response.id
