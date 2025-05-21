from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Order
from django.conf import settings

import requests
import json
import random
import hmac
import hashlib

# Create your views here.

def product_list(request):
    products = Product.objects.all()
    return render(request, 'shop/product_list.html', {'products': products})

def product_details(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_details.html', {'product': product})

def generate_authcode(msg: str) -> str:
    private_key: str = settings.VISMA_SECRET_KEY
    signature = hmac.new(
        private_key.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()

    return signature


def purchase_product(request, pk):
    url = "https://www.vismapay.com/pbwapi/auth_payment"
    api_key = settings.VISMA_API_KEY
    
    order_no = "visma_testorder_" + str(random.randint(1000, 9999999))
    auth_code = generate_authcode(api_key + "|" + order_no)

    product = get_object_or_404(Product, pk=pk)

      # luodaan _itselle_ tietokantaan tieto tilauksesta
    order = Order(
        order_name = order_no,
        product = product,
        email = "testaaja@testi.fi",
        paid = False
    )
    order.save()

    payload = {
        "version": "w3.2",
        "api_key": api_key,
        "order_number": order_no,
        "amount": int(product.total_price * 100),
        "currency": "EUR",
        "email": "test.person@example.com",
        "payment_method": {
            "type": "e-payment",
            "return_url": "http://127.0.0.1:8000/purchase_succeeded",
            "notify_url": "http://127.0.0.1:8000/purchase_succeeded",
            "lang": "fi",
            "token_valid_until": "1442403776",
        },
        "authcode": auth_code,
        "customer": {  
            "firstname": "Test",
            "lastname": "Person",
            "email": "test.person@example.com",
            "address_street": "Rasekontie 1",
            "address_city": "Raisio",
            "address_zip": "21200"
        },
        "products": [  
            {  
            "id": product.name + str(product.id),
            "title": product.name,
            "count": 1,
            "pretax_price": int(product.price * 100),
            "tax": float(product.tax),
            "price": int(product.total_price * 100),
            "type": 1
            }
        ]
    }
    hdrs = {'Content-Type' : 'application/json',}
    # Lähetetään pyyntö Vismalle
    response = requests.post(url, headers=hdrs, data=json.dumps(payload))
    print(response)
    print(response.json())
    target_url = "https://www.vismapay.com/pbwapi/token/" + response.json().get('token')

    return redirect(target_url)

def purchase_succeeded(request):
    return_code = int(request.GET.get('RETURN_CODE'))

    if return_code == 0:
        print("Purchase succeeded")
        order_no = request.GET.get('ORDER_NUMBER')
        authcode_from_visma = request.GET.get('AUTHCODE')
        settled = request.GET.get('SETTLED')

        str_for_auth = str(return_code) + "|" + order_no + "|" + settled
        print(str_for_auth)

        my_authcode = generate_authcode(str_for_auth)

        if authcode_from_visma == my_authcode:
            order = Order.objects.get(order_name=order_no)
            order.paid = True
            order.save()

    context = { 'return_code': return_code }

    return render(request, 'shop/success.html', context)

#"GET /purchase_succeeded
# ?
# AUTHCODE=F011D5D5B869DB0EFC519A07308D554471E654E1BE608890C539DE2058FADD1A
# RETURN_CODE=0
# ORDER_NUMBER=visma_testorder_3829426
# SETTLED=1 