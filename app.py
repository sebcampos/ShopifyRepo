from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from config import *
import requests
import shopify
import binascii
import os
import time
import pprint
import json

#response holding code! https://29c16721ba3c.ngrok.io/connect?code=7d85db6f98fd0023ede6c1f53e573ed5&hmac=52675c076112d6b656cd6252721066002e027bd062633258188ee59d8324c05e&shop=seni-society-delivery.myshopify.com&state=98a8bd40771827aaac40e52647bee2&timestamp=1608294381
nonce = binascii.b2a_hex(os.urandom(15)).decode("utf-8")

url="https://seni-society-delivery.myshopify.com"

my_url="f6a591eb3159.ngrok.io"

url2 = f"https://seni-society-delivery.myshopify.com/admin/oauth/authorize?client_id={API_KEY}&scope=write_orders,read_customers&redirect_uri=https://{my_url}/connect&state={nonce}"

redirect_url= "https://"+my_url+"/connect"

#all_access_url= f"https://seni-society-delivery.myshopify.com/admin/oauth/authorize?client_id={API_KEY}&scope=read_content,write_content,read_themes,write_themes,read_products,write_products,read_product_listings,read_customers,write_customers,read_orders,write_orders,write_order_edits,read_draft_orders,write_draft_orders,read_inventory,write_inventory,read_locations,read_script_tags,write_script_tags,read_fulfillments,write_fulfillments,read_assigned_fulfillment_orders,write_assigned_fulfillment_orders,read_merchant_managed_fulfillment_orders,write_merchant_managed_fulfillment_orders,read_third_party_fulfillment_orders,write_third_party_fulfillment_orders,read_shipping,write_shipping,read_analytics,read_checkouts,write_checkouts,read_reports,write_reports,read_price_rules,write_price_rules,read_discounts,write_discounts,read_marketing_events,write_marketing_events,read_resource_feedbacks,write_resource_feedbacks,read_shopify_payments_payouts,read_shopify_payments_disputes,read_translations,write_translations,read_locales,write_locales&redirect_uri=https://{my_url}/post&state={nonce}"

app = Flask(__name__)
run_with_ngrok(app)


@app.route("/testing")
def testing_page():
    results='Tesing Stage'
    return render_template("welcome.html",result=results)

@app.route("/connect", methods=['GET','POST'])
def login_page():
    render_template("driver_login.html") 
    if request.method == "POST":
        #Cheking login credentials
        if request.form["name"] == "user@example.com" and request.form["password"] == "password789456123":
            return testing_page()
        return "<h1>Invalid credentials reload page<h1>"
    return render_template("driver_login.html") 

@app.route("/install",methods=['GET'])
def install():
    print("intalling...")
    return "install page"




if __name__ == "__main__":
   app.run()

