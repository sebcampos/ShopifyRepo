from config import *
import shopify
import binascii
import os


app_url = input("url of site")

shopify.Session.setup(api_key=API_KEY, secret=API_SECRET_KEY)

shop_url = "seni-society-delivery.myshopify.com"
api_version = '2020-10'
state = binascii.b2a_hex(os.urandom(15)).decode("utf-8")
redirect_uri = f"http://{app_url}/auth/shopify/callback"
scopes = ['read_products', 'read_orders']

newSession = shopify.Session(shop_url, api_version)
auth_url = newSession.create_permission_url(scopes, redirect_uri, state)
# redirect to auth_url

print(auth_url)