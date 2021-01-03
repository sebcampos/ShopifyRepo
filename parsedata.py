import shopify
import pandas
from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from flask_nav import Nav
from flask_nav.elements import Navbar, Subgroup, View
import random
import sqlite3
from Shopify_config import access_token
from Shopify_config import hash_function
from Shopify_config import API_SECRET_KEY
import hmac
import hashlib
import base64
import json
import datetime
import time
import os
from twilio.rest import Client
import twilio_config
from splinter import Browser


#today date string:
today_str = str(datetime.datetime.today()).split(" ")[0]
tomorrow_str = str(datetime.date.today() + datetime.timedelta(days=1)).split(" ")[0]
yesterday_str = str(datetime.date.today() - datetime.timedelta(days=1)).split(" ")[0]
print(today_str)
#requires shopify object and connection 'conn'
session = shopify.Session("https://seni-society-delivery.myshopify.com",'2020-10',access_token)
shopify.ShopifyResource.activate_session(session)
conn = sqlite3.connect('database.db')

#twilio config
client = Client(twilio_config.ACCOUNT_SID, twilio_config.AUTH_TOKEN)

#create a list of valid users
def get_usernames():
    username_lst = pandas.read_sql("select username from users", con=conn).values.tolist()

    username_lst = [i[0] for i in username_lst]

    return username_lst


#import and numbers: finds the last 20 unfulfilled orders then the first 20 items in each order
#collect payload from API call
def orders_api_call():
    results = shopify.GraphQL().execute('''query {
        orders(first:20, reverse:true,  query:"fulfillment_status:unshipped,fulfillment_status:Pending") {
            edges {
                node {
                    id
                    name
                    displayFulfillmentStatus
                    createdAt
                    lineItems(first:20) {
                        edges {
                            node {
                                name
                                id
                                quantity
                                sku
                                vendor
                                product {
                                    handle
                                    description
                                    productType
                                    storefrontId
                                    tags
                                    title
                                    vendor
                                }
                            }
                        }
                    }
                    totalPriceSet {
                        presentmentMoney {
                            amount
                        }
                    }    
                    displayAddress {
                        address1
                        address2
                        city
                        zip
                        province
                        provinceCode
                        country
                        countryCodeV2
                        latitude
                        longitude
                        id
                        name
                        phone
                    }
                }
            }
        }
    }
    ''')
    #organizing data into lists
    payload = json.loads(results)
    shopify_id = [i["node"]["id"] for i in payload['data']['orders']['edges']]
    order_ids = [i["node"]["name"] for i in payload['data']['orders']['edges']]
    fulfillment_status = [i["node"]["displayFulfillmentStatus"] for i in payload['data']['orders']['edges']]
    line_items =  [i["node"]["lineItems"]["edges"] for i in payload['data']['orders']['edges']]
    order_created_time = [i["node"]["createdAt"] for i in payload["data"]["orders"]["edges"]]
    order_create_date = [i.split("T")[0] for i in order_created_time]
    customer_data = [i["node"]["displayAddress"] for i in payload["data"]["orders"]["edges"]]
    total_price = [i["node"]["totalPriceSet"]["presentmentMoney"]["amount"] for i in payload['data']['orders']['edges']]
    df = pandas.DataFrame(list(zip(order_ids,fulfillment_status,line_items,order_created_time,order_create_date,customer_data,total_price)), columns=["order_id","fulfillment_status","line_items","order_time_raw","order_date","customer_data","order_price"])
    
    customer_names = [i["name"] for i in df["customer_data"]]

    df["customer_names"] = customer_names

    df["shopify_id"] = shopify_id


    return df

def orders_api_call_1():
    results = shopify.GraphQL().execute('''query {
        orders(first:20, reverse:true, query:"fulfillment_status:unshipped,fulfillment_status:Pending") {
            edges {
                node {
                    name
                    displayFulfillmentStatus

                    createdAt
                    displayAddress {
                        name
                    }
                }
            }
        }
    }    

    ''')
    payload = json.loads(results)
    order_ids = [i["node"]["name"] for i in payload['data']['orders']['edges']]
    fulfillment_status = [i["node"]["displayFulfillmentStatus"] for i in payload['data']['orders']['edges']]
    order_created_time = [i["node"]["createdAt"] for i in payload["data"]["orders"]["edges"]]
    order_create_date = [i.split("T")[0] for i in order_created_time]
    names = [i["node"]["displayAddress"]["name"] for i in payload["data"]["orders"]["edges"]]
    df = pandas.DataFrame(list(zip(order_ids,fulfillment_status,order_create_date,order_created_time,names)), columns=["order_ids","fulfillment_status","order_date","order_time_raw","name"])
    return df

def verify_session(confirmed_session):
    token = request.args.get('token')
    user = request.args.get('user')
    if confirmed_session[user] == token:
        return user,token
    else:
        return False


#Collect items data
def items_data_call(update = False): #<-- rename this 
    
    if update == True:
        browser = Browser('firefox', executable_path="/usr/local/bin/geckodriver", headless=False)
        url = 'https://accounts.shopify.com/store-login'
        shop_domain = 'seni-society-delivery.myshopify.com'
        account_email = 'mr.robot7823465@gmail.com'
        account_password = '!Shopifysucks1'
        browser.visit(url)
        browser.find_by_id("shop_domain").fill(shop_domain)
        browser.find_by_name("commit").click()
        browser.find_by_id("account_email").fill(account_email)
        browser.find_by_name("commit").click()
        browser.find_by_id("account_password").fill(account_password)
        browser.find_by_name("commit").click()
        browser.find_by_text('Products').click()
        browser.find_by_text('Export').click()
        time.sleep(30)
        browser.quit()
        #raw_df.to_sql("items_data",con=conn, index=False)
        return f"products csv sent to {account_email}"

    
    
    #replace with a webscrape to collect this csv
    raw_df = pandas.read_csv("products_export_1.csv")
    
    raw_df.dropna(how="all",inplace=True)

    raw_df.columns = [i.replace(" ","-") for i in raw_df.columns] 


    lst = []
    for i in raw_df.columns:
        column = []
        for c in raw_df[i]:
            if type(c) == str:
                column.append(c)
            else:
                column.append(None)
        lst.append(column)
    
    inventory_df = raw_df[["Title","Variant-SKU","Variant-Inventory-Qty"]].dropna()
    inventory_df.columns = ['display_name','sku','inventory_quantity']

    return inventory_df

#create new user and related tables
def create_user(username,password):
    username_lst = get_usernames()
    #check to see if user exists
    if username in username_lst:
        return f"Aborted:\nUsername {username} already exists"

    new_user_df = items_data_call()
    #set inventory to 0
    new_user_df["inventory_quantity"] = 0
    
    password = hash_function(password)

    conn.execute(f'INSERT INTO users (username, hash_key) VALUES ("{username}","{password}")')

    new_user_df.to_sql(f'{username}',con=conn,if_exists="fail")

    new_user_orders_df = pandas.DataFrame(columns=["order_id","fulfillment_status","line_items","order_time_raw","order_date","customer_data","order_price","customer_names","accepted","completed"])
    new_user_orders_df.to_sql(f'{username}_orders',con=conn,index=False,if_exists="fail")

    conn.commit()

  
#clear session function
def clear_shopify_session():
    shopify.ShopifyResource.clear_session()

def verify_webhook(data, hmac_header):
    digest = hmac.new(API_SECRET_KEY, data.encode('utf-8'), hashlib.sha256).digest()
    computed_hmac = base64.b64encode(digest)
    return hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8'))

def clean_orders_df(raw_df,item):
    raw_df = raw_df.copy()
    df = raw_df.loc[raw_df.order_id == item]
    df["line_items"] = df["line_items"].astype('str')
    df["customer_data"] = df["customer_data"].astype('str')
    df["accepted"] = datetime.datetime.now()
    df["completed"] = None 
    return df

def order_details_parser(item,v2=False):
    raw_df = orders_api_call()
    line_items = raw_df.loc[raw_df.order_id == item]["line_items"].item()
    customer_info_dict = raw_df.loc[raw_df.order_id == item]["customer_data"].item()
    customer_info_dict.pop("id")
    order_price = raw_df.loc[raw_df.order_id == item]["order_price"].item()
    if v2 == True:
        graphQL_id = raw_df.loc[raw_df.order_id == item]["shopify_id"].item()
        return raw_df,line_items,customer_info_dict,order_price,graphQL_id


    return raw_df,line_items,customer_info_dict,order_price

#TODO  print/email/text data, account for "CLAIMED" orders , create routing function 

def send_canned_text(eta,customer_name,user,delivery_total):
    message_to_send = f'''ETA {eta} min\nHello {customer_name} !  This is {user} with The Sensi Society\nDelivery Total {delivery_total} cash or cash app\nPayments accepted via cash or Cash App: (+$5) Send to $SensiSociety\nDelivery drivers don’t carry change for safety purposes.\nPlease have ID READY upon delivery.\n🙏\nPS: HONESTLY the biggest help you can do is writing a review for us :)\nhttps://g.page/higher-ground-delivery/review?gm\nThank you so much for your order!\nNeed to Order again?\nLive Menu: TheSensiSociety.com'''
    client.messages.create(from_=twilio_config.MY_FIRST_TWILIO_NUMBER, to="6503392346", body=message_to_send)


def fufill_order(shopify_order_id):
    payload = shopify.GraphQL().execute(''' 
           {
               shop {
                   fulfillmentOrders(first:10, reverse:true) {
                       edges {
                           node {
                               id
                               order {
                                id
                               }
                           }
                       }
                   }
               }
           }''')
    payload = json.loads(payload)
    new_payload  = {v:i for i,v in zip([i["id"] for i in [i["node"]for i in payload["data"]["shop"]["fulfillmentOrders"]["edges"]]],[i["order"]["id"] for i in [i["node"]for i in payload["data"]["shop"]["fulfillmentOrders"]["edges"]]]) }
    #collect fulfillment order id and line item ids
    fulfillment_id = ""
    if shopify_order_id in new_payload:
        fulfillment_id = new_payload[shopify_order_id]
    
    payload = shopify.GraphQL().execute('''
        query {
    fulfillmentOrder(id: "'''+fulfillment_id+'''") {
    lineItems (first:20) {
        edges {
            node {
                id
                remainingQuantity
                totalQuantity
            }
        }
    }
    }

        }
    ''')
    
    payload = json.loads(payload)
    line_items = payload["data"]["fulfillmentOrder"]["lineItems"]["edges"]
    empty = []
    for i in line_items:
        empty.append({"id":i["node"]["id"], "quantity": i["node"]["totalQuantity"] }) 
    line_items = json.dumps(empty)
    line_items = line_items.replace('''"id"''',"id")
    line_items = line_items.replace('''"quantity"''',"quantity")
    #Shopify fulfill order
    shopify.GraphQL().execute('''
            mutation {
       fulfillmentCreateV2(fulfillment: {
         lineItemsByFulfillmentOrder: {
           fulfillmentOrderId: "'''+fulfillment_id+'''",
           fulfillmentOrderLineItems: '''+line_items+'''
         }
       }) {
         fulfillment {
           trackingInfo {
             url
             number
             company
           }
         }
       }
     }
    
     ''')
    
    #Shopify mark order paid

    shopify.GraphQL().execute('''
         mutation {
           orderMarkAsPaid(input: {id :"'''+shopify_order_id+'''"}) {
               order {
                   id
               }
               userErrors {
                   field
                   message
               }
           }
       }
     ''')
    
    
    return "fulfilled and paid"

#update user sqlite table after order is completed
def update_user_inventory_sale(line_items,user,check=False):
    sku_quantity_dict = {}
    for i in line_items:
        sku_quantity_dict[ i["node"]["sku"] ] = i["node"]["quantity"]
    df = pandas.read_sql(f"select * from {user}",con=conn)
    
    if check == True:
        new_dict = {}
        for i in sku_quantity_dict:
            if i in df.sku.tolist():
                quantity = sku_quantity_dict[i]
                if df.loc[df.sku == i, "inventory_quantity"].item() >= quantity:
                    new_dict[df.loc[df.sku == i, "display_name"].item()] = True
                else:
                    new_dict[df.loc[df.sku == i, "display_name"].item()] = False
        return new_dict
                

    
    
    for i in sku_quantity_dict:
        if i in df.sku.tolist():
            quantity = sku_quantity_dict[i]
            df.loc[df.sku == i, "inventory_quantity"] -= quantity
    return df.to_sql(f"{user}", con=conn, index=False, if_exists="replace")


def driver_week_summary(username,dates):
    #last date must be a monday
    df = pandas.read_sql(f"select * from {username}_orders",con=conn)
    df = df.loc[(pandas.to_datetime(df.completed) > pandas.to_datetime(dates[0])) & (pandas.to_datetime(df.completed) < pandas.to_datetime(dates[1])) & (df.fulfillment_status == "FULFILLED")]

    driver_estimate_pay = df.order_price.count() * 15
    total_money_brought_in = df.order_price.sum()
    total_orders_delivered = df.completed.count()
    print(f"Estimate Pay:\t\t\t{driver_estimate_pay}\nTotal Collected:\t\t{total_money_brought_in}\nOrders Delivered:\t\t{total_orders_delivered}\n")
    print(f"Orders for {dates[0]} to {dates[1]}:")
    for i in range(len(df.completed.tolist())):
        print("\t","CUSTOMER",df.customer_names.tolist()[i],"\n\t ORDER PRICE",df.order_price.tolist()[i],"\n\t","TIMESTAMP",df.completed.tolist()[i],"\n")

    return df