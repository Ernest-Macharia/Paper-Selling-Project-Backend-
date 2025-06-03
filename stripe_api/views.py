import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.conf import settings
import os

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@require_POST
def create_stripe_session(request):
    import json
    data = json.loads(request.body)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': data['title'],
                },
                'unit_amount': int(float(data['amount']) * 100),  # convert to cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://d19e-41-90-172-100.ngrok-free.app/api/stripe_api/stripe-payment-success/',
        cancel_url='https://d19e-41-90-172-100.ngrok-free.app/api/stripe_api/stripe-payment-cancelled/',
    )

    return JsonResponse({'id': session.id})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = 'whsec_Bhn68PPG7VNKqD3rGdpUNzqt4EjmV2xa'

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(f"✅ Payment complete for session: {session['id']}")

    return HttpResponse(status=200)


def stripe_payment_success(request):
    return HttpResponse("<h1>✅ Payment was successful!</h1><p>Thank you for your purchase.</p>")


def stripe_payment_cancelled(request):
    return HttpResponse("<h1>❌ Payment was cancelled.</h1><p>You can try again at any time.</p>")
