# WhatsApp Pro — Plataforma Web Completa (Django)

Plataforma web completa basada en Django + Django REST Framework para gestión integral de campañas de WhatsApp con automatizaciones, seguimientos y analíticas.

## 🎯 Características Principales

### Core Features
- ✅ Panel web responsive (Django templates + Bootstrap 5.3.2) para PC/tablet/móvil
- ✅ API REST completa con 9 endpoints y acciones personalizadas
- ✅ **Gestión completa de contactos**: Crear, editar, eliminar, filtros, acciones masivas
- ✅ **Importación múltiple**: CSV/Excel, lista de números, WhatsApp (próximamente)
- ✅ Sistema de plantillas con variables dinámicas
- ✅ Campañas de mensajería masiva con estadísticas
- ✅ Worker asíncrono para procesamiento de mensajes
- ✅ Adapter intercambiable para Twilio/360dialog

### Features Avanzadas de Contactos
- ✅ **Búsqueda y filtros**: Por nombre, teléfono, email, grupo, estado, etiquetas
- ✅ **Acciones masivas**: Cambiar grupo, agregar etiquetas, opt-in/out, eliminar
- ✅ **Importación desde archivos**: CSV y Excel con detección automática de columnas
- ✅ **Importación desde texto**: Lista de números con formato flexible
- ✅ **Gestión de grupos**: Crear y asignar grupos dinámicamente
- ✅ **Sistema de etiquetas**: Clasificación múltiple con badges visuales
- ✅ **Estadísticas en tiempo real**: Total, opt-in, opt-out, grupos

### Features Avanzadas del Sistema
- ✅ **Tags (Etiquetas)**: Organiza contactos con etiquetas de colores
- ✅ **Rules (Reglas)**: Respuestas automáticas con condiciones y prioridad
- ✅ **Workflows**: Automatizaciones con disparadores, delays y acciones
- ✅ **Follow-Ups**: Sistema de seguimientos y recordatorios
- ✅ **Attachments**: Gestión de archivos multimedia (imágenes, audio, video, documentos)
- ✅ **Analytics**: Panel de analíticas con métricas y reportes
- ✅ **Importadores**: CSV/Excel para contactos, JSON para plantillas/workflows

## 📊 Estado de Migración

**Progreso total:** ~95% completado

- Modelos: 9/9 (100%)
- Vistas Web: 13/13 (100%) - ✨ **Nueva: Gestión completa de contactos**
- Templates: 18/18 (100%) - ✨ **Nuevas: contact_form, contact_confirm_delete, contacts_import**
- APIs REST: 9/9 (100%)
- Comandos: 4/4 (100%)
- Gestión de Contactos: 100% (crear, editar, eliminar, importar, filtros, acciones masivas)

## Estructura Principal

```
whatsapp-pro/
├── manage.py
├── requirements.txt
├── README.md
├── .env.example
├── proj/                      # Configuración Django
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── whatsapp/                  # App principal
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py             # Contact, Template, Campaign, OutgoingMessage
│   ├── admin.py              # Configuración Django Admin
│   ├── views.py              # Vistas web
│   ├── urls.py               # URLs web
│   ├── api.py                # ViewSets API REST
│   ├── serializers.py        # Serializadores DRF
│   ├── utils.py              # Utilidades (limpiar_telefono, process_template)
│   ├── send_adapter.py       # Adapter de envío (stub simulado)
│   ├── send_adapter_twilio.py # Adapter Twilio (listo para usar)
│   └── management/
│       └── commands/
│           ├── import_contacts.py   # Importar CSV/XLSX
│           ├── import_plantillas.py # Importar plantillas.json
│           ├── import_workflows.py  # Importar workflows.json
│           └── run_worker.py        # Worker para procesar mensajes
└── templates/                 # Templates Django
    ├── base.html
    └── whatsapp/
        ├── index.html
        ├── contact_list.html
        ├── template_list.html
        ├── campaign_list.html
        ├── campaign_detail.html
        └── message_list.html
```

## Requisitos (Local)

- Python 3.10 o 3.11
- pip
- Recomendado: virtualenv

## Instalación Local

### 1. Crear y activar virtualenv

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
py -3 -m venv venv
venv\Scripts\activate.bat
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y ajusta los valores:

```bash
cp .env.example .env
```

Edita `.env`:
```
DJANGO_SECRET_KEY=tu_secret_key_aqui
DEBUG=1
SENDER_PHONE_NUMBER=+1234567890
```

### 4. Ejecutar migraciones

```bash
python manage.py migrate
```

### 5. Crear superuser

```bash
python manage.py createsuperuser
```

### 6. Levantar servidor

```bash
python manage.py runserver
```

Accede a:
- Web UI: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/api/

## 📂 Gestión de Contactos

### Interfaz Web Completa

Accede a http://127.0.0.1:8000/contacts/ para:

#### Funcionalidades Principales
- **Visualización**: Tabla interactiva con todos los contactos y sus datos
- **Búsqueda**: Por nombre, teléfono o email en tiempo real
- **Filtros**: Por grupo, estado opt-in/out, etiquetas
- **Estadísticas**: Contador de total, opt-in, opt-out y grupos

#### Acciones Individuales
- **Crear**: Formulario web para agregar contactos uno a uno
- **Editar**: Actualizar datos de contactos existentes
- **Eliminar**: Con confirmación de seguridad

#### Acciones Masivas (Selección múltiple)
- Marcar como **Opt-In** o **Opt-Out**
- Cambiar de **grupo** (asignar a grupos existentes o crear nuevos)
- Agregar **etiquetas** a múltiples contactos
- **Eliminar** contactos en lote con confirmación

#### Métodos de Importación

**1. Desde Archivo CSV/Excel**
- Formato: CSV, XLSX, XLS
- Detección automática de columnas (nombre, teléfono, email, grupo)
- Actualiza contactos existentes o crea nuevos
- Reporta importados/actualizados/errores

**2. Desde Lista de Números**
- Pega una lista de números directamente
- Formatos soportados:
  - `Nombre|+593987654321` (con nombre)
  - `+593987654321` (solo número)
  - `0987654321` (agrega código de país +593 automático)
- Asigna grupo por defecto

**3. Desde WhatsApp (Próximamente)**
- Importar miembros de grupos de WhatsApp
- Importar desde contactos de WhatsApp Business
- Requiere integración con proveedor (Twilio/360dialog)

### Importar desde Terminal (CLI)

```bash
python manage.py import_contacts path/to/contacts.csv
```

El CSV debe tener columnas con nombre y teléfono. Ejemplos soportados:
- `nombre`, `name`, `full_name`
- `telefono`, `phone`, `phone_number`, `whatsapp`

**Ejemplo CSV:**
```csv
nombre,telefono,grupo,email
Juan Pérez,+593987654321,Líderes,juan@example.com
María García,+593987654322,General,maria@example.com
```

## Importar Otros Datos

### Importar Plantillas (desde proyecto anterior)

Si tienes un archivo `plantillas.json`:

```bash
python manage.py import_plantillas path/to/plantillas.json
```

### Importar Workflows/Campañas (desde proyecto anterior)

Si tienes un archivo `workflows.json`:

```bash
python manage.py import_workflows path/to/workflows.json
```

**Nota:** Importa plantillas ANTES de workflows, ya que las campañas dependen de plantillas existentes.

## Probar Envío (Local, Simulado)

1. **Crear Template** desde Admin o API
2. **Crear Campaign** asociada a un Template
3. **Encolar mensajes** desde la UI (botón "Enqueue") o API (`POST /api/campaigns/{id}/enqueue/`)
4. **Ejecutar worker** en otra terminal:

```bash
python manage.py run_worker
```

El worker procesará mensajes pendientes usando el adapter stub (simula envíos).

## 🌐 URLs de Acceso

### Interfaz Web
- **Dashboard**: http://127.0.0.1:8000/
- **Contactos**: http://127.0.0.1:8000/contacts/ ✨ **NUEVA GESTIÓN COMPLETA**
  - Crear: http://127.0.0.1:8000/contacts/create/
  - Importar: http://127.0.0.1:8000/contacts/import/
- **Plantillas**: http://127.0.0.1:8000/templates/
- **Campañas**: http://127.0.0.1:8000/campaigns/
- **Etiquetas**: http://127.0.0.1:8000/tags/
- **Reglas**: http://127.0.0.1:8000/rules/
- **Workflows**: http://127.0.0.1:8000/workflows/
- **Seguimientos**: http://127.0.0.1:8000/followups/
- **Archivos**: http://127.0.0.1:8000/attachments/
- **Analíticas**: http://127.0.0.1:8000/analytics/
- **Admin**: http://127.0.0.1:8000/admin/

### API REST
- **Base API**: http://127.0.0.1:8000/api/
- Ver documentación completa en [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## API Endpoints

Ver documentación completa en [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### Resumen de Endpoints

**Tags:**
- `GET/POST /api/tags/` - Lista y crea etiquetas
- `GET /api/tags/{id}/contacts/` - Contactos de una etiqueta

**Contacts:**
- `GET/POST /api/contacts/` - Lista y crea contactos
- `GET /api/contacts/by_group/` - Contactos agrupados
- `POST /api/contacts/{id}/add_tag/` - Agregar etiqueta

**Templates:**
- `GET/POST /api/templates/` - Lista y crea plantillas
- `GET /api/templates/active/` - Solo plantillas activas

**Campaigns:**
- `GET/POST /api/campaigns/` - Lista y crea campañas
- `POST /api/campaigns/{id}/enqueue/` - Encola mensajes
- `GET /api/campaigns/{id}/stats/` - Estadísticas

**Messages:**
- `GET /api/messages/` - Lista mensajes salientes
- `GET /api/messages/by_status/` - Mensajes por estado

**Rules:**
- `GET/POST /api/rules/` - Lista y crea reglas
- `POST /api/rules/{id}/toggle_active/` - Activar/desactivar
- `POST /api/rules/{id}/test/` - Probar regla

**Workflows:**
- `GET/POST /api/workflows/` - Lista y crea workflows
- `POST /api/workflows/{id}/toggle_active/` - Activar/desactivar
- `GET /api/workflows/by_trigger/` - Filtrar por disparador

**FollowUps:**
- `GET/POST /api/followups/` - Lista y crea seguimientos
- `POST /api/followups/{id}/complete/` - Marcar completado
- `GET /api/followups/pending/` - Solo pendientes
- `GET /api/followups/overdue/` - Solo vencidos

**Attachments:**
- `GET/POST /api/attachments/` - Lista y sube archivos
- `GET /api/attachments/by_type/` - Filtrar por tipo

## 🌐 URLs Web Disponibles

- **Dashboard:** http://127.0.0.1:8000/
- **Admin:** http://127.0.0.1:8000/admin/ (CRUD completo)
- **API REST:** http://127.0.0.1:8000/api/

### Secciones Web

- **Contactos:** `/contacts/`
- **Plantillas:** `/templates/`
- **Campañas:** `/campaigns/`
- **Etiquetas:** `/tags/`
- **Reglas Auto:** `/rules/`
- **Workflows:** `/workflows/`
- **Seguimientos:** `/followups/`
- **Archivos:** `/attachments/`
- **Analíticas:** `/analytics/`

## Siguientes Pasos (Post-MVP)

1. **Conectar proveedor real** (Twilio/360dialog): reemplazar `whatsapp/utils/send_adapter.py`
2. **Migrar a Postgres & Redis + Celery** para producción
3. **Configurar hosting y dominio**
4. **Añadir roles y permisos** multi-organización si es necesario
5. **Implementar webhooks** para recibir respuestas

## Notas de Privacidad y Cumplimiento

- ✅ Guarda opt-ins en BD (campo `opt_in` en Contact)
- ⚠️ No envíes mensajes masivos por Selenium en producción
- 🔒 En producción: habilitar HTTPS y gestionar secrets de forma segura

## Licencia

Uso interno para iglesias/organizaciones.
