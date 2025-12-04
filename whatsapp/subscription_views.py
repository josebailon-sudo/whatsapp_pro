from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Subscription, Payment
from datetime import timedelta

@login_required
def subscription_status(request):
    """Muestra el estado de la suscripción del usuario"""
    subscription, created = Subscription.objects.get_or_create(user=request.user)
    subscription.check_and_update_status()
    
    # Historial de pagos
    payments = subscription.payments.filter(verified=True).order_by('-created_at')
    
    context = {
        'subscription': subscription,
        'payments': payments,
    }
    return render(request, 'subscription/status.html', context)


@login_required
def subscription_activate(request):
    """Página de activación de suscripción"""
    subscription, created = Subscription.objects.get_or_create(user=request.user)
    subscription.check_and_update_status()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'activate_initial':
            # Activar plan inicial de 3 meses
            payment_method = request.POST.get('payment_method')
            transaction_id = request.POST.get('transaction_id', '')
            
            # Crear registro de pago pendiente
            payment = Payment.objects.create(
                subscription=subscription,
                amount=45,
                payment_method=payment_method,
                plan_type='initial',
                transaction_id=transaction_id,
                notes=f'Activación inicial - 3 meses',
                verified=False  # Admin debe verificar
            )
            
            messages.success(request, 
                '✅ Pago registrado. Un administrador verificará tu pago en breve y activará tu cuenta.')
            return redirect('subscription_status')
        
        elif action == 'activate_monthly':
            # Renovación mensual
            if not subscription.has_paid_initial:
                messages.error(request, 
                    '❌ Primero debes activar el plan inicial de 3 meses.')
                return redirect('subscription_activate')
            
            payment_method = request.POST.get('payment_method')
            transaction_id = request.POST.get('transaction_id', '')
            
            # Crear registro de pago pendiente
            payment = Payment.objects.create(
                subscription=subscription,
                amount=15,
                payment_method=payment_method,
                plan_type='monthly',
                transaction_id=transaction_id,
                notes=f'Renovación mensual',
                verified=False
            )
            
            messages.success(request, 
                '✅ Pago registrado. Tu suscripción se renovará una vez verificado el pago.')
            return redirect('subscription_status')
    
    context = {
        'subscription': subscription,
    }
    return render(request, 'subscription/activate.html', context)


@login_required
def subscription_payment_instructions(request):
    """Instrucciones de pago"""
    subscription = Subscription.objects.get(user=request.user)
    
    # Determinar qué plan debe pagar
    if not subscription.has_paid_initial:
        plan = 'initial'
        amount = 45
        duration = '3 meses'
    else:
        plan = 'monthly'
        amount = 15
        duration = '1 mes'
    
    context = {
        'subscription': subscription,
        'plan': plan,
        'amount': amount,
        'duration': duration,
    }
    return render(request, 'subscription/payment_instructions.html', context)
