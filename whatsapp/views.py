from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import (
    Contact, Template, Campaign, OutgoingMessage,
    Tag, Rule, Workflow, FollowUp, Attachment
)
from .utils import process_template
from .send_adapter import check_whatsapp_status, get_qr_code
import json
import requests
import os

def index(request):
    """Vista principal del dashboard con estadísticas."""
    from datetime import timedelta
    
    # Detectar si el usuario es nuevo (sin contactos ni campañas)
    total_contacts = Contact.objects.count()
    total_campaigns = Campaign.objects.count()
    is_new_user = (total_contacts == 0 and total_campaigns == 0)
    
    # Si el usuario fuerza el modo (parámetro ?mode=wizard o ?mode=expert)
    force_mode = request.GET.get('mode', '')
    
    recent_campaigns = Campaign.objects.all().order_by('-created_at')[:5]
    
    context = {
        'total_contacts': total_contacts,
        'total_templates': Template.objects.filter(active=True).count(),
        'total_campaigns': total_campaigns,
        'pending_messages': OutgoingMessage.objects.filter(status='pending').count(),
        'messages_sent_today': OutgoingMessage.objects.filter(
            sent_at__date=timezone.now().date()
        ).count(),
        'total_tags': Tag.objects.count(),
        'active_rules': Rule.objects.filter(active=True).count(),
        'active_workflows': Workflow.objects.filter(active=True).count(),
        'pending_followups': FollowUp.objects.filter(status='pendiente').count(),
        'recent_campaigns': recent_campaigns,
        'is_new_user': is_new_user,
        'show_wizard_suggestion': is_new_user and force_mode != 'expert',
    }
    return render(request, 'index.html', context)

def contacts_list(request):
    """Vista principal de gestión de contactos con filtros y acciones masivas."""
    # Filtros
    search_query = request.GET.get('search', '')
    group_filter = request.GET.get('group', '')
    opt_in_filter = request.GET.get('opt_in', '')
    tag_filter = request.GET.get('tag', '')
    
    contacts = Contact.objects.all()
    
    if search_query:
        contacts = contacts.filter(
            Q(name__icontains=search_query) | 
            Q(phone__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    if group_filter:
        contacts = contacts.filter(group=group_filter)
    
    if opt_in_filter:
        contacts = contacts.filter(opt_in=(opt_in_filter == 'true'))
    
    if tag_filter:
        contacts = contacts.filter(tags__id=tag_filter)
    
    contacts = contacts.order_by('name').distinct()
    
    # Acciones masivas
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_contacts')
        
        if selected_ids:
            if action == 'delete':
                Contact.objects.filter(id__in=selected_ids).delete()
                messages.success(request, f'{len(selected_ids)} contacto(s) eliminado(s)')
            elif action == 'opt_out':
                Contact.objects.filter(id__in=selected_ids).update(opt_in=False)
                messages.success(request, f'{len(selected_ids)} contacto(s) marcado(s) como opt-out')
            elif action == 'opt_in':
                Contact.objects.filter(id__in=selected_ids).update(opt_in=True)
                messages.success(request, f'{len(selected_ids)} contacto(s) marcado(s) como opt-in')
            elif action == 'change_group':
                new_group = request.POST.get('new_group', 'General')
                Contact.objects.filter(id__in=selected_ids).update(group=new_group)
                messages.success(request, f'{len(selected_ids)} contacto(s) movido(s) a grupo "{new_group}"')
            elif action == 'add_tag':
                tag_id = request.POST.get('tag_id')
                if tag_id:
                    tag = Tag.objects.get(id=tag_id)
                    for contact_id in selected_ids:
                        contact = Contact.objects.get(id=contact_id)
                        contact.tags.add(tag)
                    messages.success(request, f'Etiqueta "{tag.name}" agregada a {len(selected_ids)} contacto(s)')
        
        return redirect('contacts_list')
    
    # Estadísticas
    stats = {
        'total': Contact.objects.count(),
        'opt_in': Contact.objects.filter(opt_in=True).count(),
        'opt_out': Contact.objects.filter(opt_in=False).count(),
        'groups': Contact.objects.values('group').distinct().count(),
    }
    
    # Listas de valores para filtros
    groups = Contact.objects.values_list('group', flat=True).distinct().order_by('group')
    tags = Tag.objects.all().order_by('name')
    
    # Estadísticas por grupo (para modal de administración)
    group_stats = {}
    for group in groups:
        group_stats[group] = Contact.objects.filter(group=group).count()
    
    context = {
        'contacts': contacts,
        'stats': stats,
        'groups': groups,
        'tags': tags,
        'group_stats': group_stats,
        'search_query': search_query,
        'group_filter': group_filter,
        'opt_in_filter': opt_in_filter,
        'tag_filter': tag_filter,
    }
    
    return render(request, 'contacts_list.html', context)

def contacts_delete_all(request):
    """Elimina todos los contactos de la base de datos."""
    if request.method == 'GET':
        count = Contact.objects.count()
        Contact.objects.all().delete()
        messages.warning(request, f'Se eliminaron todos los {count} contactos de la base de datos.')
    return redirect('contacts_list')

def contacts_save_group(request):
    """Guarda los contactos actuales con un nombre de grupo específico."""
    if request.method == 'POST':
        group_name = request.POST.get('group_name', '').strip()
        if not group_name:
            messages.error(request, 'Debe proporcionar un nombre de grupo.')
            return redirect('contacts_list')
        
        # Actualizar todos los contactos con el nuevo nombre de grupo
        count = Contact.objects.all().update(group=group_name)
        messages.success(request, f'Se guardaron {count} contactos en el grupo "{group_name}".')
    return redirect('contacts_list')

def contacts_delete_group(request):
    """Elimina todos los contactos de un grupo específico."""
    if request.method == 'POST':
        group_name = request.POST.get('group_name', '').strip()
        if not group_name:
            messages.error(request, 'Debe especificar un nombre de grupo.')
            return redirect('contacts_list')
        
        count = Contact.objects.filter(group=group_name).count()
        Contact.objects.filter(group=group_name).delete()
        messages.warning(request, f'Se eliminaron {count} contactos del grupo "{group_name}".')
    return redirect('contacts_list')

def templates_list(request):
    templates = Template.objects.all().order_by('-created_at')
    return render(request, 'templates_list.html', {'templates': templates})

def campaigns_list(request):
    campaigns = Campaign.objects.all().order_by('-created_at')
    return render(request, 'campaigns_list.html', {'campaigns': campaigns})

def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST' and 'enqueue' in request.POST:
        contacts = Contact.objects.filter(opt_in=True)
        created = 0
        for c in contacts:
            payload = process_template(campaign.template.content, {'nombre': c.name, 'telefono': c.phone, 'grupo': c.group})
            OutgoingMessage.objects.create(campaign=campaign, contact=c, payload=payload)
            created += 1
        
        # Actualizar estadísticas de campaña
        campaign.total_contacts = created
        campaign.save()
        
        messages.success(request, f'Enqueued {created} messages for campaign "{campaign.name}"')
        return redirect(reverse('campaign_detail', args=[pk]))
    return render(request, 'campaign_detail.html', {'campaign': campaign})

# ========== TAGS ==========
def tags_list(request):
    """Lista de etiquetas con conteo de contactos."""
    tags = Tag.objects.annotate(contact_count=Count('contacts')).order_by('name')
    return render(request, 'tags_list.html', {'tags': tags})

def tag_detail(request, pk):
    """Detalle de etiqueta con contactos asociados."""
    tag = get_object_or_404(Tag, pk=pk)
    contacts = tag.contacts.all().order_by('name')
    return render(request, 'tag_detail.html', {'tag': tag, 'contacts': contacts})

# ========== RULES ==========
def rules_list(request):
    """Lista de reglas de respuesta automática."""
    rules = Rule.objects.all().order_by('priority', 'name')
    return render(request, 'rules_list.html', {'rules': rules})

def rule_detail(request, pk):
    """Detalle de regla con edición de condiciones."""
    rule = get_object_or_404(Rule, pk=pk)
    
    if request.method == 'POST':
        # Actualizar estado activo/inactivo
        if 'toggle_active' in request.POST:
            rule.active = not rule.active
            rule.save()
            messages.success(request, f'Regla {"activada" if rule.active else "desactivada"}')
            return redirect('rule_detail', pk=pk)
    
    return render(request, 'rule_detail.html', {'rule': rule})

# ========== WORKFLOWS ==========
def workflows_list(request):
    """Lista de workflows/automatizaciones."""
    workflows = Workflow.objects.all().order_by('name')
    return render(request, 'workflows_list.html', {'workflows': workflows})

def workflow_detail(request, pk):
    """Detalle de workflow."""
    workflow = get_object_or_404(Workflow, pk=pk)
    
    if request.method == 'POST':
        if 'toggle_active' in request.POST:
            workflow.active = not workflow.active
            workflow.save()
            messages.success(request, f'Workflow {"activado" if workflow.active else "desactivado"}')
            return redirect('workflow_detail', pk=pk)
    
    return render(request, 'workflow_detail.html', {'workflow': workflow})

# ========== FOLLOW-UPS ==========
def followups_list(request):
    """Lista de seguimientos/recordatorios."""
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        followups = FollowUp.objects.filter(status=status_filter)
    else:
        followups = FollowUp.objects.all()
    
    followups = followups.order_by('scheduled_for')
    
    # Estadísticas
    stats = {
        'pendiente': FollowUp.objects.filter(status='pendiente').count(),
        'completado': FollowUp.objects.filter(status='completado').count(),
        'vencidos': FollowUp.objects.filter(
            status='pendiente',
            scheduled_for__lt=timezone.now()
        ).count(),
    }
    
    return render(request, 'followups_list.html', {
        'followups': followups,
        'stats': stats,
        'current_filter': status_filter
    })

def followup_detail(request, pk):
    """Detalle de seguimiento."""
    followup = get_object_or_404(FollowUp, pk=pk)
    
    if request.method == 'POST':
        if 'complete' in request.POST:
            followup.status = 'completado'
            followup.completed_at = timezone.now()
            followup.save()
            messages.success(request, 'Seguimiento marcado como completado')
            return redirect('followups_list')
    
    return render(request, 'followup_detail.html', {'followup': followup})

# ========== ATTACHMENTS ==========
def attachments_list(request):
    """Lista de archivos adjuntos."""
    attachments = Attachment.objects.all().order_by('-uploaded_at')
    
    type_filter = request.GET.get('type', '')
    if type_filter:
        attachments = attachments.filter(type=type_filter)
    
    stats = {
        'total': Attachment.objects.count(),
        'images': Attachment.objects.filter(type='image').count(),
        'documents': Attachment.objects.filter(type='document').count(),
    }
    
    return render(request, 'attachments_list.html', {
        'attachments': attachments,
        'stats': stats,
        'current_filter': type_filter
    })

# ========== CONTACTS MANAGEMENT ==========
def _process_file_with_mapping(request):
    """Procesa el archivo usando el mapeo de columnas seleccionado por el usuario."""
    try:
        import pandas as pd
        import base64
        from io import BytesIO
        from .utils import limpiar_telefono
        
        # Recuperar archivo de sesión
        file_content = request.session.get('import_file')
        filename = request.session.get('import_filename')
        
        if not file_content or not filename:
            messages.error(request, '❌ Sesión expirada. Por favor, vuelva a seleccionar el archivo.')
            return redirect('contacts_import')
        
        # Decodificar archivo
        file_bytes = base64.b64decode(file_content)
        file_like = BytesIO(file_bytes)
        
        # Leer archivo
        if filename.endswith('.csv'):
            df = pd.read_csv(file_like)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_like, engine='openpyxl')
        
        # Obtener mapeo de columnas del formulario
        name_col = request.POST.get('name_column')
        phone_col = request.POST.get('phone_column')
        email_col = request.POST.get('email_column')
        group_col = request.POST.get('group_column')
        custom_field1_col = request.POST.get('custom_field1_column')
        custom_field2_col = request.POST.get('custom_field2_column')
        
        # Validar columnas obligatorias
        if not name_col or not phone_col:
            messages.error(request, '❌ Debe seleccionar al menos las columnas de Nombre y Teléfono.')
            return redirect('contacts_import')
        
        # Procesar filas
        imported = 0
        updated = 0
        errors = 0
        error_details = []
        
        for idx, row in df.iterrows():
            try:
                # Extraer datos según mapeo
                name = str(row[name_col]).strip() if name_col in row else ''
                phone_raw = str(row[phone_col]).strip() if phone_col in row else ''
                
                if not name or name == 'nan':
                    errors += 1
                    error_details.append(f"Fila {idx+2}: nombre vacío")
                    continue
                
                phone = limpiar_telefono(phone_raw)
                if not phone or phone == 'nan' or phone == '+593':
                    errors += 1
                    error_details.append(f"Fila {idx+2}: teléfono inválido '{phone_raw}'")
                    continue
                
                # Campos opcionales
                email = ''
                if email_col and email_col in row:
                    email = str(row[email_col]).strip()
                    if email == 'nan':
                        email = ''
                
                group = 'General'
                if group_col and group_col in row:
                    group = str(row[group_col]).strip()
                    if group == 'nan':
                        group = 'General'
                
                # Campos personalizados (guardar en notes o crear campos custom)
                notes_parts = []
                if custom_field1_col and custom_field1_col in row:
                    value = str(row[custom_field1_col]).strip()
                    if value and value != 'nan':
                        notes_parts.append(f"{custom_field1_col}: {value}")
                
                if custom_field2_col and custom_field2_col in row:
                    value = str(row[custom_field2_col]).strip()
                    if value and value != 'nan':
                        notes_parts.append(f"{custom_field2_col}: {value}")
                
                notes = ' | '.join(notes_parts) if notes_parts else ''
                
                # Crear o actualizar contacto
                contact, created = Contact.objects.update_or_create(
                    phone=phone,
                    defaults={
                        'name': name,
                        'email': email,
                        'group': group,
                        'opt_in': True,
                        'notes': notes  # Aquí guardamos los campos personalizados
                    }
                )
                
                if created:
                    imported += 1
                else:
                    updated += 1
                    
            except Exception as e:
                errors += 1
                error_details.append(f"Fila {idx+2}: {str(e)}")
                continue
        
        # Limpiar sesión
        del request.session['import_file']
        del request.session['import_filename']
        
        # Mensaje de resultado
        if imported > 0 or updated > 0:
            messages.success(request, f'✅ Importación completada: {imported} nuevos, {updated} actualizados, {errors} errores')
            if error_details and len(error_details) <= 5:
                messages.warning(request, f'Detalles de errores: {"; ".join(error_details)}')
        else:
            messages.error(request, f'❌ No se pudo importar ningún contacto. Errores: {errors}')
            if error_details:
                messages.warning(request, f'Primeros errores: {"; ".join(error_details[:3])}')
        
        return redirect('contacts_list')
        
    except Exception as e:
        messages.error(request, f'❌ Error al procesar archivo: {str(e)}')
        import traceback
        print(f"Error detallado: {traceback.format_exc()}")
        return redirect('contacts_import')

def contact_create(request):
    """Crear nuevo contacto individualmente."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        group = request.POST.get('group', 'General').strip()
        opt_in = request.POST.get('opt_in') == 'on'
        tag_ids = request.POST.getlist('tags')
        
        if not name or not phone:
            messages.error(request, 'Nombre y teléfono son obligatorios')
        else:
            # Limpiar teléfono
            from .utils import limpiar_telefono
            phone_clean = limpiar_telefono(phone)
            
            # Verificar duplicados
            if Contact.objects.filter(phone=phone_clean).exists():
                messages.error(request, f'Ya existe un contacto con el teléfono {phone_clean}')
            else:
                contact = Contact.objects.create(
                    name=name,
                    phone=phone_clean,
                    email=email,
                    group=group,
                    opt_in=opt_in
                )
                
                # Agregar tags
                if tag_ids:
                    for tag_id in tag_ids:
                        contact.tags.add(tag_id)
                
                messages.success(request, f'Contacto "{name}" creado exitosamente')
                return redirect('contacts_list')
    
    # GET: mostrar formulario
    groups = Contact.objects.values_list('group', flat=True).distinct().order_by('group')
    tags = Tag.objects.all().order_by('name')
    
    return render(request, 'contact_form.html', {
        'mode': 'create',
        'groups': groups,
        'tags': tags,
    })

def contact_edit(request, pk):
    """Editar contacto existente."""
    contact = get_object_or_404(Contact, pk=pk)
    
    if request.method == 'POST':
        contact.name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        contact.email = request.POST.get('email', '').strip()
        contact.group = request.POST.get('group', 'General').strip()
        contact.opt_in = request.POST.get('opt_in') == 'on'
        tag_ids = request.POST.getlist('tags')
        
        if not contact.name or not phone:
            messages.error(request, 'Nombre y teléfono son obligatorios')
        else:
            from .utils import limpiar_telefono
            phone_clean = limpiar_telefono(phone)
            
            # Verificar duplicados (excepto el mismo contacto)
            if Contact.objects.filter(phone=phone_clean).exclude(pk=pk).exists():
                messages.error(request, f'Ya existe otro contacto con el teléfono {phone_clean}')
            else:
                contact.phone = phone_clean
                contact.save()
                
                # Actualizar tags
                contact.tags.clear()
                if tag_ids:
                    for tag_id in tag_ids:
                        contact.tags.add(tag_id)
                
                messages.success(request, f'Contacto "{contact.name}" actualizado')
                return redirect('contacts_list')
    
    # GET: mostrar formulario con datos actuales
    groups = Contact.objects.values_list('group', flat=True).distinct().order_by('group')
    tags = Tag.objects.all().order_by('name')
    current_tag_ids = list(contact.tags.values_list('id', flat=True))
    
    return render(request, 'contact_form.html', {
        'mode': 'edit',
        'contact': contact,
        'groups': groups,
        'tags': tags,
        'current_tag_ids': current_tag_ids,
    })

def contact_delete(request, pk):
    """Eliminar contacto individual."""
    contact = get_object_or_404(Contact, pk=pk)
    
    if request.method == 'POST':
        name = contact.name
        contact.delete()
        messages.success(request, f'Contacto "{name}" eliminado')
        return redirect('contacts_list')
    
    return render(request, 'contact_confirm_delete.html', {'contact': contact})

def contacts_import(request):
    """Importar contactos desde diferentes fuentes."""
    if request.method == 'POST':
        import_type = request.POST.get('import_type')
        
        # Importar desde archivo CSV/XLSX
        if import_type == 'file':
            # Paso 1: Si el usuario está mapeando columnas (viene de la vista previa)
            if 'column_mapping' in request.POST:
                return _process_file_with_mapping(request)
            
            # Paso 2: Subir archivo y mostrar vista previa para mapeo
            if 'file' not in request.FILES:
                messages.error(request, '❌ No se seleccionó ningún archivo. Por favor, haga clic en "Seleccionar archivo" primero.')
                return redirect('contacts_import')
            
            file = request.FILES['file']
            
            # Validar extensión
            if not (file.name.endswith('.csv') or file.name.endswith('.xlsx') or file.name.endswith('.xls')):
                messages.error(request, f'❌ Formato no soportado: {file.name}. Use archivos CSV, XLSX o XLS.')
                return redirect('contacts_import')
            
            try:
                # Leer archivo y guardar en sesión para el siguiente paso
                import pandas as pd
                import base64
                
                # Leer archivo
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file, engine='openpyxl')
                
                # Guardar archivo en sesión (como base64)
                file.seek(0)
                file_content = base64.b64encode(file.read()).decode('utf-8')
                request.session['import_file'] = file_content
                request.session['import_filename'] = file.name
                
                # Obtener columnas y preview de datos
                columns = list(df.columns)
                preview_data = df.head(5).to_dict('records')
                
                # Renderizar vista de mapeo
                context = {
                    'columns': columns,
                    'preview_data': preview_data,
                    'filename': file.name,
                    'total_rows': len(df),
                }
                return render(request, 'contacts_import_mapping.html', context)
                
            except Exception as e:
                import pandas as pd
                from .utils import limpiar_telefono
                
                # Leer archivo
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file, engine='openpyxl')
                
                # Detectar columnas de forma FLEXIBLE
                # Si el archivo tiene encabezados reconocibles, úsalos
                # Si no, usa las primeras 2 columnas por defecto
                
                # Intentar detectar columna de nombre
                name_col = None
                for c in df.columns:
                    if any(x in str(c).lower() for x in ['name', 'nombre', 'contacto', 'persona']):
                        name_col = c
                        break
                if name_col is None:
                    name_col = df.columns[0]  # Primera columna por defecto
                
                # Intentar detectar columna de teléfono
                phone_col = None
                for c in df.columns:
                    if any(x in str(c).lower() for x in ['phone', 'telefono', 'tel', 'cel', 'whatsapp', 'móvil', 'movil', 'celular', 'número', 'numero']):
                        phone_col = c
                        break
                if phone_col is None:
                    # Si hay al menos 2 columnas, usar la segunda
                    if len(df.columns) >= 2:
                        phone_col = df.columns[1]
                    else:
                        messages.error(request, '❌ El archivo debe tener al menos 2 columnas: Nombre y Teléfono.')
                        return redirect('contacts_import')
                
                # Detectar columnas opcionales (email, grupo)
                email_col = None
                for c in df.columns:
                    if any(x in str(c).lower() for x in ['email', 'correo', 'mail', 'e-mail']):
                        email_col = c
                        break
                
                group_col = None
                for c in df.columns:
                    if any(x in str(c).lower() for x in ['group', 'grupo', 'categoria', 'categoría', 'tipo']):
                        group_col = c
                        break
                
                # Procesar filas
                imported = 0
                updated = 0
                errors = 0
                error_details = []
                
                for idx, row in df.iterrows():
                    try:
                        name = str(row[name_col]).strip()
                        phone_raw = str(row[phone_col]).strip()
                        phone = limpiar_telefono(phone_raw)
                        
                        if not phone or phone == 'nan' or phone == '+593':
                            errors += 1
                            error_details.append(f"Fila {idx+2}: teléfono inválido '{phone_raw}'")
                            continue
                        
                        email = str(row[email_col]).strip() if email_col and email_col in row else ''
                        if email == 'nan':
                            email = ''
                        
                        group = str(row[group_col]).strip() if group_col and group_col in row else 'General'
                        if group == 'nan':
                            group = 'General'
                        
                        contact, created = Contact.objects.update_or_create(
                            phone=phone,
                            defaults={'name': name, 'email': email, 'group': group, 'opt_in': True}
                        )
                        
                        if created:
                            imported += 1
                        else:
                            updated += 1
                    except Exception as e:
                        errors += 1
                        error_details.append(f"Fila {idx+2}: {str(e)}")
                        continue
                
                # Mensaje de resultado
                if imported > 0 or updated > 0:
                    messages.success(request, f'✅ Importación completada: {imported} nuevos, {updated} actualizados, {errors} errores')
                    if error_details and len(error_details) <= 5:
                        messages.warning(request, f'Detalles de errores: {"; ".join(error_details)}')
                else:
                    messages.error(request, f'❌ No se pudo importar ningún contacto. Errores: {errors}')
                    if error_details:
                        messages.warning(request, f'Primeros errores: {"; ".join(error_details[:3])}')
                
                return redirect('contacts_list')
                
            except Exception as e:
                messages.error(request, f'❌ Error al procesar archivo: {str(e)}. Verifique que el archivo tenga el formato correcto.')
                import traceback
                print(f"Error detallado: {traceback.format_exc()}")  # Para debug en consola
                return redirect('contacts_import')
        
        # Importar desde texto (lista de números)
        elif import_type == 'text':
            text_input = request.POST.get('text_input', '').strip()
            default_group = request.POST.get('default_group', 'General').strip()
            
            if not text_input:
                messages.error(request, 'Ingrese números de teléfono')
            else:
                from .utils import limpiar_telefono
                lines = text_input.split('\n')
                imported = 0
                errors = 0
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Formato: "Nombre|Teléfono" o solo "Teléfono"
                    parts = line.split('|') if '|' in line else [line]
                    
                    if len(parts) == 2:
                        name = parts[0].strip()
                        phone_raw = parts[1].strip()
                    else:
                        phone_raw = parts[0].strip()
                        name = phone_raw  # Usar teléfono como nombre si no hay nombre
                    
                    phone = limpiar_telefono(phone_raw)
                    
                    if not phone:
                        errors += 1
                        continue
                    
                    try:
                        Contact.objects.update_or_create(
                            phone=phone,
                            defaults={'name': name, 'group': default_group, 'opt_in': True}
                        )
                        imported += 1
                    except Exception:
                        errors += 1
                
                messages.success(request, f'{imported} contacto(s) importado(s), {errors} errores')
                return redirect('contacts_list')
        
        # Importar desde WhatsApp (placeholder - requiere integración)
        elif import_type == 'whatsapp_group':
            messages.warning(request, 'Importar desde grupos de WhatsApp requiere integración con proveedor (Twilio/360dialog). Funcionalidad pendiente.')
        
        elif import_type == 'whatsapp_contacts':
            messages.warning(request, 'Importar desde contactos de WhatsApp requiere integración con proveedor. Funcionalidad pendiente.')
    
    # GET: mostrar formulario de importación
    groups = Contact.objects.values_list('group', flat=True).distinct().order_by('group')
    
    return render(request, 'contacts_import.html', {'groups': groups})

# ========== ANALYTICS ==========
def analytics(request):
    """Panel de analíticas y reportes."""
    campaigns_stats = Campaign.objects.values('name', 'total_contacts', 'sent_count', 'failed_count')[:10]
    messages_by_status = OutgoingMessage.objects.values('status').annotate(count=Count('id'))
    contacts_by_group = Contact.objects.values('group').annotate(count=Count('id')).order_by('-count')[:10]
    tags_usage = Tag.objects.annotate(contact_count=Count('contacts')).order_by('-contact_count')[:10]
    
    seven_days_ago = timezone.now() - timezone.timedelta(days=7)
    recent_campaigns = Campaign.objects.filter(created_at__gte=seven_days_ago).count()
    recent_messages = OutgoingMessage.objects.filter(created_at__gte=seven_days_ago).count()
    
    context = {
        'campaigns_stats': list(campaigns_stats),
        'messages_by_status': list(messages_by_status),
        'contacts_by_group': list(contacts_by_group),
        'tags_usage': tags_usage,
        'recent_campaigns': recent_campaigns,
        'recent_messages': recent_messages,
    }
    
    return render(request, 'analytics.html', context)

# ========== TEMPLATES (PLANTILLAS) MANAGEMENT ==========
def template_create(request):
    """Crear nueva plantilla de mensaje."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', 'General').strip()
        active = request.POST.get('active') == 'on'
        
        if not name or not content:
            messages.error(request, '❌ Nombre y contenido son obligatorios')
        else:
            try:
                template = Template.objects.create(
                    name=name,
                    content=content,
                    category=category,
                    active=active
                )
                messages.success(request, f'✅ Plantilla "{template.name}" creada exitosamente')
                return redirect('templates_list')
            except Exception as e:
                messages.error(request, f'❌ Error al crear plantilla: {str(e)}')
    
    # Variables disponibles
    available_vars = ['nombre', 'telefono', 'grupo', 'email', 'fecha', 'hora', 'saludo']
    categories = Template.objects.values_list('category', flat=True).distinct().order_by('category')
    
    # Ejemplo de contacto para vista previa
    sample_contact = Contact.objects.first()
    
    context = {
        'available_vars': available_vars,
        'categories': categories,
        'sample_contact': sample_contact,
    }
    
    return render(request, 'template_create.html', context)

def template_edit(request, pk):
    """Editar plantilla existente."""
    template = get_object_or_404(Template, pk=pk)
    
    if request.method == 'POST':
        template.name = request.POST.get('name', '').strip()
        template.content = request.POST.get('content', '').strip()
        template.category = request.POST.get('category', 'General').strip()
        template.active = request.POST.get('active') == 'on'
        
        if not template.name or not template.content:
            messages.error(request, '❌ Nombre y contenido son obligatorios')
        else:
            try:
                template.save()
                messages.success(request, f'✅ Plantilla "{template.name}" actualizada exitosamente')
                return redirect('templates_list')
            except Exception as e:
                messages.error(request, f'❌ Error al actualizar plantilla: {str(e)}')
    
    # Variables disponibles
    available_vars = ['nombre', 'telefono', 'grupo', 'email', 'fecha', 'hora', 'saludo']
    categories = Template.objects.values_list('category', flat=True).distinct().order_by('category')
    
    # Ejemplo de contacto para vista previa
    sample_contact = Contact.objects.first()
    
    context = {
        'template': template,
        'available_vars': available_vars,
        'categories': categories,
        'sample_contact': sample_contact,
    }
    
    return render(request, 'template_edit.html', context)

def template_delete(request, pk):
    """Eliminar plantilla."""
    template = get_object_or_404(Template, pk=pk)
    
    if request.method == 'POST':
        # Verificar si está siendo usada en campañas
        campaigns_using = Campaign.objects.filter(template=template).count()
        
        if campaigns_using > 0:
            messages.error(request, f'❌ No se puede eliminar. Esta plantilla está siendo usada en {campaigns_using} campaña(s)')
            return redirect('templates_list')
        
        template_name = template.name
        template.delete()
        messages.success(request, f'✅ Plantilla "{template_name}" eliminada')
        return redirect('templates_list')
    
    return render(request, 'template_delete.html', {'template': template})

# ========== CAMPAIGNS MANAGEMENT ==========
def campaign_create(request):
    """Crear nueva campaña con diseñador de mensajes."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        template_id = request.POST.get('template_id')
        
        # Filtros de contactos
        filter_type = request.POST.get('filter_type', 'all')
        selected_groups = request.POST.getlist('groups[]')
        selected_tags = request.POST.getlist('tags[]')
        selected_contacts = request.POST.getlist('contacts[]')
        
        # Programación
        schedule_type = request.POST.get('schedule_type', 'now')
        scheduled_date = request.POST.get('scheduled_date')
        scheduled_time = request.POST.get('scheduled_time')
        
        if not name or not template_id:
            messages.error(request, '❌ Nombre y plantilla son obligatorios')
        else:
            try:
                template = Template.objects.get(pk=template_id)
                
                # Crear campaña
                scheduled_for = None
                if schedule_type == 'scheduled' and scheduled_date and scheduled_time:
                    from django.utils.dateparse import parse_datetime
                    scheduled_for = parse_datetime(f"{scheduled_date}T{scheduled_time}")
                
                campaign = Campaign.objects.create(
                    name=name,
                    template=template,
                    scheduled_for=scheduled_for,
                    created_by=request.user.username if request.user.is_authenticated else 'admin'
                )
                
                # Filtrar contactos según selección
                if filter_type == 'all':
                    contacts = Contact.objects.filter(opt_in=True)
                elif filter_type == 'groups':
                    contacts = Contact.objects.filter(opt_in=True, group__in=selected_groups)
                elif filter_type == 'tags':
                    contacts = Contact.objects.filter(opt_in=True, tags__id__in=selected_tags).distinct()
                elif filter_type == 'custom':
                    contacts = Contact.objects.filter(opt_in=True, id__in=selected_contacts)
                else:
                    contacts = Contact.objects.filter(opt_in=True)
                
                # Actualizar contador de contactos
                campaign.total_contacts = contacts.count()
                campaign.save()
                
                messages.success(request, f'✅ Campaña "{campaign.name}" creada con {campaign.total_contacts} contactos. Ahora puedes encolar los mensajes.')
                return redirect('campaign_detail', pk=campaign.pk)
                
            except Template.DoesNotExist:
                messages.error(request, '❌ Plantilla no encontrada')
            except Exception as e:
                messages.error(request, f'❌ Error al crear campaña: {str(e)}')
    
    # GET: mostrar formulario
    templates = Template.objects.filter(active=True).order_by('name')
    groups = Contact.objects.values_list('group', flat=True).distinct().order_by('group')
    tags = Tag.objects.all().order_by('name')
    contacts = Contact.objects.filter(opt_in=True).order_by('name')
    
    # Estadísticas
    total_contacts = Contact.objects.filter(opt_in=True).count()
    contacts_by_group = {}
    for group in groups:
        contacts_by_group[group] = Contact.objects.filter(opt_in=True, group=group).count()
    
    context = {
        'templates': templates,
        'groups': groups,
        'tags': tags,
        'contacts': contacts,
        'total_contacts': total_contacts,
        'contacts_by_group': contacts_by_group,
    }
    
    return render(request, 'campaign_create.html', context)

def campaign_send(request, pk):
    """Encolar mensajes de la campaña para envío."""
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if request.method == 'POST':
        try:
            # Verificar si ya hay mensajes encolados
            existing_messages = OutgoingMessage.objects.filter(campaign=campaign).count()
            
            if existing_messages > 0:
                messages.warning(request, f'⚠️ Esta campaña ya tiene {existing_messages} mensajes encolados. ¿Desea agregar más?')
                # Aquí podrías agregar lógica adicional si es necesario
            
            # Obtener contactos según filtros de la campaña
            # Por ahora, obtenemos todos los contactos opt-in
            contacts = Contact.objects.filter(opt_in=True)
            
            # Si la campaña tiene filtros específicos guardados, aplicarlos aquí
            # TODO: Guardar filtros en Campaign model para reutilizarlos
            
            created_count = 0
            for contact in contacts:
                # Procesar plantilla con datos del contacto
                from .utils import process_template
                payload = process_template(
                    campaign.template.content,
                    {
                        'nombre': contact.name,
                        'telefono': contact.phone,
                        'grupo': contact.group,
                        'email': contact.email,
                    }
                )
                
                # Crear mensaje pendiente
                OutgoingMessage.objects.create(
                    campaign=campaign,
                    contact=contact,
                    payload=payload,
                    status='pending'
                )
                created_count += 1
            
            # Actualizar estadísticas de campaña
            campaign.total_contacts = created_count
            campaign.save()
            
            messages.success(request, f'✅ {created_count} mensajes encolados exitosamente. El worker los procesará automáticamente.')
            return redirect('campaign_detail', pk=campaign.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error al encolar mensajes: {str(e)}')
            return redirect('campaign_detail', pk=campaign.pk)
    
    return redirect('campaign_detail', pk=campaign.pk)


def quick_send(request):
    """Envío rápido - escribir y enviar mensaje sin guardar plantilla"""
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        recipient_filter = request.POST.get('recipient_filter', 'all')
        selected_groups = request.POST.getlist('groups')
        selected_contacts = request.POST.getlist('contacts')
        
        if not message_text:
            messages.error(request, '❌ Debes escribir un mensaje.')
            return redirect('quick_send')
        
        # Crear campaña temporal para tracking
        temp_campaign = Campaign.objects.create(
            name=f"Envío Rápido {timezone.now().strftime('%d/%m/%Y %H:%M')}",
            template=None,  # Sin plantilla para envíos rápidos
            created_by=request.user.username if request.user.is_authenticated else 'admin'
        )
        
        # Obtener destinatarios
        contacts = Contact.objects.filter(opt_in=True)
        
        if recipient_filter == 'groups' and selected_groups:
            contacts = contacts.filter(group__in=selected_groups)
        elif recipient_filter == 'custom' and selected_contacts:
            contacts = contacts.filter(id__in=selected_contacts)
        
        # Crear y encolar mensajes
        created_count = 0
        for contact in contacts:
            # Procesar mensaje con variables del contacto
            processed_message = process_template(
                message_text,
                {
                    'nombre': contact.name,
                    'telefono': contact.phone,
                    'grupo': contact.group,
                    'email': contact.email,
                }
            )
            
            OutgoingMessage.objects.create(
                campaign=temp_campaign,
                contact=contact,
                payload=processed_message,
                status='pending'
            )
            created_count += 1
        
        # Actualizar total de contactos
        temp_campaign.total_contacts = created_count
        temp_campaign.save()
        
        messages.success(request, f'✅ Envío rápido creado! {created_count} mensajes en cola.')
        return redirect('campaign_detail', pk=temp_campaign.id)
    
    # GET request - mostrar formulario
    groups = Contact.objects.values_list('group', flat=True).distinct().exclude(group='')
    contacts = Contact.objects.filter(opt_in=True).order_by('name')
    sample_contact = Contact.objects.first()
    
    available_vars = ['nombre', 'telefono', 'grupo', 'email', 'fecha', 'hora', 'saludo']
    
    context = {
        'groups': groups,
        'contacts': contacts,
        'sample_contact': sample_contact,
        'available_vars': available_vars,
    }
    
    return render(request, 'quick_send.html', context)


# ========== WIZARD GUIADO ==========
def wizard_welcome(request):
    """Bienvenida del asistente paso a paso"""
    stats = {
        'total_contacts': Contact.objects.count(),
        'total_templates': Template.objects.count(),
        'total_campaigns': Campaign.objects.count(),
    }
    return render(request, 'wizard/welcome.html', {'stats': stats})

def wizard_step1_contacts(request):
    """Paso 1: Importar/Verificar contactos"""
    contacts = Contact.objects.filter(opt_in=True)
    groups = contacts.values_list('group', flat=True).distinct()
    
    stats = {
        'total': contacts.count(),
        'by_group': {},
    }
    
    for group in groups:
        stats['by_group'][group] = contacts.filter(group=group).count()
    
    # Guardar en sesión que completó este paso
    if contacts.count() > 0:
        request.session['wizard_step1_completed'] = True
    
    context = {
        'contacts': contacts[:20],  # Mostrar primeros 20
        'stats': stats,
        'has_contacts': contacts.count() > 0,
    }
    
    return render(request, 'wizard/step1_contacts.html', context)

def wizard_step2_message(request):
    """Paso 2: Crear mensaje"""
    if not request.session.get('wizard_step1_completed'):
        messages.warning(request, '⚠️ Primero debes completar el Paso 1: Contactos')
        return redirect('wizard_step1')
    
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        send_mode = request.POST.get('send_mode', 'single')  # single o multiline
        
        if not message_text:
            messages.error(request, '❌ Debes escribir un mensaje')
            return redirect('wizard_step2')
        
        # Guardar mensaje y configuración en sesión
        request.session['wizard_message'] = message_text
        request.session['wizard_send_mode'] = send_mode
        request.session['wizard_step2_completed'] = True
        
        # Manejar archivos adjuntos
        if request.FILES.get('attachment'):
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import os
            
            attachment = request.FILES['attachment']
            # Guardar en media/attachments/
            file_path = default_storage.save(f'attachments/{attachment.name}', ContentFile(attachment.read()))
            
            # Detectar tipo
            ext = attachment.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                att_type = 'image'
            elif ext in ['mp4', 'avi', 'mov', 'webm']:
                att_type = 'video'
            elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                att_type = 'audio'
            else:
                att_type = 'document'
            
            request.session['wizard_attachment'] = {
                'path': file_path,
                'type': att_type,
                'name': attachment.name,
            }
        
        messages.success(request, f'✅ Mensaje guardado! Modo: {"Multi-línea" if send_mode == "multiline" else "Mensaje único"}')
        return redirect('wizard_step3')
    
    # GET: mostrar formulario
    groups = Contact.objects.values_list('group', flat=True).distinct().exclude(group='')
    contacts = Contact.objects.filter(opt_in=True).order_by('name')
    sample_contact = Contact.objects.first()
    available_vars = ['nombre', 'telefono', 'grupo', 'email', 'fecha', 'hora', 'saludo']
    
    # Recuperar mensaje guardado
    saved_message = request.session.get('wizard_message', '')
    saved_mode = request.session.get('wizard_send_mode', 'single')
    saved_attachment = request.session.get('wizard_attachment', None)
    
    context = {
        'groups': groups,
        'contacts': contacts,
        'sample_contact': sample_contact,
        'available_vars': available_vars,
        'saved_message': saved_message,
        'saved_mode': saved_mode,
        'saved_attachment': saved_attachment,
    }
    
    return render(request, 'wizard/step2_message.html', context)

def wizard_step3_whatsapp(request):
    """Paso 3: Conectar WhatsApp"""
    if not request.session.get('wizard_step2_completed'):
        messages.warning(request, '⚠️ Primero debes completar el Paso 2: Mensaje')
        return redirect('wizard_step2')
    
    # Verificar estado de WhatsApp real
    whatsapp_status = check_whatsapp_status()
    is_connected = whatsapp_status.get('connected', False) and whatsapp_status.get('status') == 'ready'
    
    if request.method == 'POST':
        connection_method = request.POST.get('connection_method', 'whatsapp_real')
        
        if connection_method == 'whatsapp_real':
            # Verificar que esté conectado antes de continuar
            if not is_connected:
                messages.error(request, '❌ Debes conectar WhatsApp primero escaneando el código QR')
                return redirect('wizard_step3')
        
        request.session['wizard_connection_method'] = connection_method
        request.session['wizard_step3_completed'] = True
        
        if connection_method == 'whatsapp_real':
            messages.success(request, '✅ WhatsApp conectado! Ahora configura el envío.')
        else:
            messages.info(request, 'ℹ️ Modo simulado activado para pruebas.')
        
        return redirect('wizard_step4')
    
    context = {
        'current_method': request.session.get('wizard_connection_method', 'whatsapp_real'),
        'whatsapp_status': whatsapp_status,
        'is_connected': is_connected,
    }
    
    return render(request, 'wizard/step3_whatsapp.html', context)

def wizard_step4_preview(request):
    """Paso 4: Vista previa y configuración de envío"""
    if not request.session.get('wizard_step3_completed'):
        messages.warning(request, '⚠️ Primero debes completar el Paso 3: Conexión')
        return redirect('wizard_step3')
    
    if request.method == 'POST':
        # Crear campaña con toda la configuración
        message_text = request.session.get('wizard_message', '')
        recipient_filter = request.POST.get('recipient_filter', 'all')
        selected_groups = request.POST.getlist('groups')
        selected_contacts = request.POST.getlist('contacts')
        
        # Configuración de envío
        send_speed = int(request.POST.get('send_speed', 10))
        batch_size = int(request.POST.get('batch_size', 50))
        delay_between_batches = int(request.POST.get('delay_between_batches', 60))
        
        # Calcular delay entre mensajes
        delay_between_messages = 60.0 / send_speed if send_speed > 0 else 6.0
        
        # Crear o obtener template temporal
        template_obj, created = Template.objects.get_or_create(
            name=f"Wizard {timezone.now().strftime('%Y%m%d_%H%M%S')}",
            defaults={
                'content': message_text,
                'active': True
            }
        )
        if not created:
            template_obj.content = message_text
            template_obj.save()
        
        # Crear campaña
        campaign = Campaign.objects.create(
            name=f"Campaña Wizard {timezone.now().strftime('%d/%m/%Y %H:%M')}",
            template=template_obj,
            created_by=request.user.username if request.user.is_authenticated else 'admin',
            send_speed=send_speed,
            batch_size=batch_size,
            delay_between_batches=delay_between_batches,
            delay_between_messages=delay_between_messages,
            status='ready'
        )
        
        # Obtener contactos
        contacts = Contact.objects.filter(opt_in=True)
        
        if recipient_filter == 'groups' and selected_groups:
            contacts = contacts.filter(group__in=selected_groups)
        elif recipient_filter == 'custom' and selected_contacts:
            contacts = contacts.filter(id__in=selected_contacts)
        
        # Obtener configuración de envío
        send_mode = request.session.get('wizard_send_mode', 'single')
        attachment_data = request.session.get('wizard_attachment', None)
        
        # Crear mensajes
        created_count = 0
        for contact in contacts:
            processed_message = process_template(
                message_text,
                {
                    'nombre': contact.name,
                    'telefono': contact.phone,
                    'grupo': contact.group,
                    'email': contact.email,
                }
            )
            
            if send_mode == 'multiline':
                # Separar por líneas y crear un mensaje por cada línea
                lines = [line.strip() for line in processed_message.split('\n') if line.strip()]
                
                # Crear mensaje padre
                parent = OutgoingMessage.objects.create(
                    campaign=campaign,
                    contact=contact,
                    payload=processed_message,  # Mensaje completo
                    status='pending',
                    line_number=0,
                    attachment_path=attachment_data['path'] if attachment_data else None,
                    attachment_type=attachment_data['type'] if attachment_data else None,
                )
                
                # Crear mensaje por cada línea
                for i, line in enumerate(lines, start=1):
                    OutgoingMessage.objects.create(
                        campaign=campaign,
                        contact=contact,
                        payload=line,
                        status='pending',
                        line_number=i,
                        parent_message=parent,
                        attachment_path=attachment_data['path'] if attachment_data and i == 1 else None,
                        attachment_type=attachment_data['type'] if attachment_data and i == 1 else None,
                    )
                created_count += 1
            else:
                # Mensaje único
                OutgoingMessage.objects.create(
                    campaign=campaign,
                    contact=contact,
                    payload=processed_message,
                    status='pending',
                    line_number=0,
                    attachment_path=attachment_data['path'] if attachment_data else None,
                    attachment_type=attachment_data['type'] if attachment_data else None,
                )
                created_count += 1
        
        campaign.total_contacts = created_count
        campaign.save()
        
        # Limpiar sesión del wizard
        request.session.pop('wizard_message', None)
        request.session.pop('wizard_send_mode', None)
        request.session.pop('wizard_attachment', None)
        request.session.pop('wizard_step1_completed', None)
        request.session.pop('wizard_step2_completed', None)
        request.session.pop('wizard_step3_completed', None)
        request.session.pop('wizard_connection_method', None)
        
        messages.success(request, f'✅ Campaña creada con {created_count} mensajes!')
        return redirect('wizard_launch', campaign_id=campaign.id)
    
    # GET: mostrar preview
    message_text = request.session.get('wizard_message', '')
    groups = Contact.objects.values_list('group', flat=True).distinct().exclude(group='')
    contacts = Contact.objects.filter(opt_in=True).order_by('name')
    sample_contact = Contact.objects.first()
    
    # Preview del mensaje
    preview_message = ''
    if sample_contact:
        preview_message = process_template(
            message_text,
            {
                'nombre': sample_contact.name,
                'telefono': sample_contact.phone,
                'grupo': sample_contact.group,
                'email': sample_contact.email,
            }
        )
    
    context = {
        'message_text': message_text,
        'preview_message': preview_message,
        'groups': groups,
        'contacts': contacts,
        'sample_contact': sample_contact,
        'total_contacts': contacts.count(),
    }
    
    return render(request, 'wizard/step4_preview.html', context)

def wizard_launch(request, campaign_id):
    """Vista de lanzamiento y monitoreo en tiempo real"""
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            campaign.status = 'sending'
            campaign.save()
            messages.success(request, '🚀 Campaña iniciada! Los mensajes se están enviando.')
        
        elif action == 'pause':
            campaign.status = 'paused'
            campaign.save()
            messages.info(request, '⏸️ Campaña pausada.')
        
        elif action == 'resume':
            campaign.status = 'sending'
            campaign.save()
            messages.success(request, '▶️ Campaña reanudada.')
        
        elif action == 'cancel':
            campaign.status = 'cancelled'
            campaign.save()
            # Marcar todos los mensajes pendientes como cancelados
            campaign.messages.filter(status='pending').update(status='cancelled')
            messages.warning(request, '🛑 Campaña cancelada. Los mensajes pendientes no se enviarán.')
        
        elif action == 'cleanup':
            # Eliminar mensajes cancelados y fallidos
            deleted_cancelled = campaign.messages.filter(status='cancelled').delete()[0]
            deleted_failed = campaign.messages.filter(status='failed').delete()[0]
            total_deleted = deleted_cancelled + deleted_failed
            messages.success(request, f'🧹 Limpieza completada: {total_deleted} mensajes eliminados ({deleted_cancelled} cancelados, {deleted_failed} fallidos)')
        
        return redirect('wizard_launch', campaign_id=campaign_id)
    
    # Estadísticas en tiempo real
    messages_stats = {
        'pending': campaign.messages.filter(status='pending').count(),
        'sending': campaign.messages.filter(status='sending').count(),
        'sent': campaign.messages.filter(status='sent').count(),
        'failed': campaign.messages.filter(status='failed').count(),
        'cancelled': campaign.messages.filter(status='cancelled').count(),
    }
    
    recent_messages = campaign.messages.all().order_by('-created_at')[:10]
    
    # Calcular progreso
    total = campaign.total_contacts
    completed = messages_stats['sent'] + messages_stats['failed']
    progress_percent = (completed / total * 100) if total > 0 else 0
    
    context = {
        'campaign': campaign,
        'messages_stats': messages_stats,
        'recent_messages': recent_messages,
        'progress_percent': progress_percent,
        'is_active': campaign.status == 'sending',
    }
    
    return render(request, 'wizard/launch.html', context)


# ============================================
# WhatsApp Connection Views
# ============================================

def whatsapp_connection(request):
    """Vista para mostrar el estado de conexión de WhatsApp y QR code"""
    return render(request, 'whatsapp_connection.html')

def whatsapp_status(request):
    """API endpoint para verificar el estado de WhatsApp"""
    status = check_whatsapp_status()
    
    # Si está conectado, obtener info adicional
    if status['connected'] and status['status'] == 'ready':
        try:
            service_url = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:3000')
            response = requests.get(f"{service_url}/info", timeout=5)
            if response.status_code == 200:
                info_data = response.json()
                status['info'] = info_data.get('info', {})
        except:
            pass
    
    return JsonResponse(status)

@csrf_exempt
def whatsapp_logout(request):
    """Cerrar sesión de WhatsApp"""
    if request.method == 'POST':
        try:
            service_url = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:3000')
            response = requests.post(f"{service_url}/logout", timeout=10)
            if response.status_code == 200:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Error al cerrar sesión'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
