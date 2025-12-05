const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const express = require('express');
const bodyParser = require('body-parser');
require('dotenv').config();

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3000;

// Inicializar cliente de WhatsApp
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './whatsapp_session'
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    }
});

let isReady = false;
let qrCodeData = null;

// Evento: Generar QR
client.on('qr', (qr) => {
    console.log('📱 QR Code generado. Escanéalo con WhatsApp:');
    qrcode.generate(qr, { small: true });
    qrCodeData = qr;
});

// Evento: Cliente listo
client.on('ready', () => {
    console.log('✅ WhatsApp Web conectado y listo!');
    isReady = true;
    qrCodeData = null;
});

// Evento: Autenticación exitosa
client.on('authenticated', () => {
    console.log('🔐 Autenticación exitosa');
});

// Evento: Error de autenticación
client.on('auth_failure', (msg) => {
    console.error('❌ Error de autenticación:', msg);
});

// Evento: Desconexión
client.on('disconnected', (reason) => {
    console.log('⚠️ Cliente desconectado:', reason);
    isReady = false;
});

// Inicializar cliente
console.log('🚀 Iniciando WhatsApp Web.js...');
client.initialize();

// ============================================
// API REST Endpoints
// ============================================

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'initializing',
        qr: qrCodeData,
        timestamp: new Date().toISOString()
    });
});

// Obtener QR Code
app.get('/qr', async (req, res) => {
    if (isReady) {
        return res.json({ status: 'ready', message: 'Ya estás conectado' });
    }
    
    if (qrCodeData) {
        try {
            // Convertir QR a imagen base64
            const qrImage = await QRCode.toDataURL(qrCodeData);
            return res.json({ 
                status: 'qr_available', 
                qr: qrImage  // data:image/png;base64,...
            });
        } catch (err) {
            return res.json({ 
                status: 'qr_available', 
                qr: qrCodeData  // Texto plano como fallback
            });
        }
    }
    
    res.json({ status: 'initializing', message: 'Generando QR...' });
});

// Enviar mensaje de texto
app.post('/send', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({ 
                success: false, 
                error: 'WhatsApp no está conectado. Escanea el QR primero.' 
            });
        }

        const { phone, message } = req.body;
        
        if (!phone || !message) {
            return res.status(400).json({ 
                success: false, 
                error: 'Se requieren "phone" y "message"' 
            });
        }

        // Formatear número (agregar @c.us si no lo tiene)
        const chatId = phone.includes('@c.us') ? phone : `${phone}@c.us`;
        
        // Enviar mensaje
        const sentMessage = await client.sendMessage(chatId, message);
        
        console.log(`✓ Mensaje enviado a ${phone}: ${message.substring(0, 50)}...`);
        
        res.json({ 
            success: true, 
            messageId: sentMessage.id.id,
            timestamp: sentMessage.timestamp 
        });

    } catch (error) {
        console.error('❌ Error enviando mensaje:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// Enviar mensaje con adjunto (imagen, video, audio, documento)
app.post('/send-media', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({ 
                success: false, 
                error: 'WhatsApp no está conectado' 
            });
        }

        const { phone, message, mediaPath, mediaType } = req.body;
        
        if (!phone || !mediaPath) {
            return res.status(400).json({ 
                success: false, 
                error: 'Se requieren "phone" y "mediaPath"' 
            });
        }

        const chatId = phone.includes('@c.us') ? phone : `${phone}@c.us`;
        
        // Cargar archivo
        const media = MessageMedia.fromFilePath(mediaPath);
        
        // Enviar con caption opcional
        const sentMessage = await client.sendMessage(chatId, media, { 
            caption: message || '' 
        });
        
        console.log(`✓ Media enviado a ${phone}: ${mediaType || 'file'}`);
        
        res.json({ 
            success: true, 
            messageId: sentMessage.id.id,
            timestamp: sentMessage.timestamp 
        });

    } catch (error) {
        console.error('❌ Error enviando media:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// Verificar si un número existe en WhatsApp
app.post('/check-number', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({ success: false, error: 'WhatsApp no conectado' });
        }

        const { phone } = req.body;
        const numberId = await client.getNumberId(phone);
        
        res.json({ 
            success: true, 
            exists: numberId !== null,
            numberId: numberId ? numberId._serialized : null
        });

    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Obtener info del cliente
app.get('/info', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(503).json({ success: false, error: 'WhatsApp no conectado' });
        }

        const info = client.info;
        res.json({ 
            success: true, 
            info: {
                wid: info.wid._serialized,
                platform: info.platform,
                phone: info.wid.user
            }
        });

    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Cerrar sesión
app.post('/logout', async (req, res) => {
    try {
        await client.logout();
        isReady = false;
        res.json({ success: true, message: 'Sesión cerrada' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🌐 Servidor WhatsApp Web.js escuchando en puerto ${PORT}`);
    console.log(`📡 Endpoints disponibles:`);
    console.log(`   GET  /health        - Estado del servicio`);
    console.log(`   GET  /qr            - Obtener QR code`);
    console.log(`   POST /send          - Enviar mensaje`);
    console.log(`   POST /send-media    - Enviar archivo`);
    console.log(`   POST /check-number  - Verificar número`);
    console.log(`   GET  /info          - Info del cliente`);
    console.log(`   POST /logout        - Cerrar sesión`);
});

// Manejo de errores no capturados
process.on('unhandledRejection', (error) => {
    console.error('❌ Unhandled rejection:', error);
});
