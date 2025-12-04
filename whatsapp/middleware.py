from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone

class SubscriptionMiddleware:
    """Middleware que verifica el estado de la suscripción"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que NO requieren suscripción activa
        self.exempt_urls = [
            '/admin/',
            '/accounts/login/',
            '/accounts/logout/',
            '/subscription/activate/',
            '/subscription/status/',
            '/subscription/payment/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # Verificar si la URL está exenta
        if any(request.path.startswith(url) for url in self.exempt_urls):
            response = self.get_response(request)
            return response
        
        # Solo verificar para usuarios autenticados
        if request.user.is_authenticated:
            # Superusuarios tienen acceso total
            if request.user.is_superuser:
                response = self.get_response(request)
                return response
            
            # Verificar suscripción
            try:
                subscription = request.user.subscription
                subscription.check_and_update_status()
                
                # Si está expirada o suspendida, redirigir a página de activación
                if subscription.status in ['expired', 'suspended']:
                    if request.path != reverse('subscription_activate'):
                        messages.warning(request, 
                            f'Tu suscripción ha vencido. Por favor activa tu cuenta para continuar.')
                        return redirect('subscription_activate')
                
                # Advertencia si faltan menos de 7 días
                elif subscription.days_remaining <= 7 and subscription.days_remaining > 0:
                    if not request.session.get('subscription_warning_shown'):
                        messages.warning(request, 
                            f'⚠️ Tu suscripción vence en {subscription.days_remaining} días. Renueva pronto para evitar interrupciones.')
                        request.session['subscription_warning_shown'] = True
            
            except:
                # Si no tiene suscripción, crear una en modo trial
                from whatsapp.models import Subscription
                subscription = Subscription.objects.create(user=request.user)
                messages.success(request, 
                    f'🎉 ¡Bienvenido! Tienes 30 días de prueba gratuita.')
        
        response = self.get_response(request)
        return response
