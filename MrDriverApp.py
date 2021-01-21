import shopify
import pandas
from flask import Flask, redirect, url_for, request, render_template, session, send_from_directory
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
import stdiomask 
from twilio.rest import Client
import twilio_config
from splinter import Browser
import requests
import re


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


'''Login Page_____________________________________________________________________________________'''


#verify login 
def login_page_verification(confirmed_session):
    df = pandas.read_sql("select * from users", con=conn)
    username_lst = get_usernames()
    #Cheking login credentials
    if request.form["name"] in username_lst and request.form["name"] != "admin" and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
        user = request.form["name"]
        token= "".join([str(random.randint(1,30)) for i in range(0,5)])
        confirmed_session[user] = token
        print(confirmed_session)
        return "user",user,token
    elif request.form["name"] == 'admin' and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
        user = request.form["name"]
        token= "".join([str(random.randint(1,30)) for i in range(0,5)])
        confirmed_session[user] = token
        return "admin",user,token
    return False


'''User Inventory_________________________________________________________________________________'''


#collect data for items details page
def collect_items_details_data(user):
    sku = request.args.get('item').split("__")[1]
    df = pandas.read_sql(f"select * from {user} where sku='{sku}'", con=conn)
    df_raw_item = pandas.read_sql(f'''select * from items_data where "Variant SKU"='{sku}' ''', con=conn)
    html_data = df_raw_item['Body (HTML)'].item()
    price = df_raw_item['Variant Price'].item()
    image = df_raw_item['Image Src'].item()
    return df,sku,html_data,price,image



#post handler for item_details page 
def item_details_post_handler(user,sku,token):
    new_val = request.form["updateme"]
    conn.execute(f"UPDATE {user} SET inventory_quantity={new_val} WHERE sku='{sku}'")
    conn.commit()
    return user, sku, token

'''Orders for USER________________________________________________________________________________'''


#collect data for user orders page
def collect_user_orders_data(user):
    df = pandas.read_sql(f"select * from {user}_orders",con=conn)
    df.accepted = df.accepted.apply(lambda x: str(x).split(".")[0])
    df.completed = df.completed.apply(lambda x: str(x).split(".")[0])
    html_df = df.loc[df.fulfillment_status == "UNFULFILLED"][["order_id","fulfillment_status","order_date","customer_names","accepted","completed"]]
    return html_df


def user_orders_post_handler(user,token):
        if list(request.form.keys())[0] == 'item':
            item = request.form["item"]
            return "item",item
        if list(request.form.keys())[0] == 'route':
            lat,lng,coords_lst = order_coords(user)
            return "route",lat,lng,coords_lst
        if list(request.form.keys())[0] == 'log':
            df = pandas.read_sql(f'select * from {user}_orders',con=conn)
            df.set_index("order_id",inplace=True)
            df.drop('line_items',axis=1,inplace=True)
            return "log",df



'''Detials for Order (USER)______________________________________________________________________'''

#collect data for specified order
def collect_user_order_details(user):
    item = request.args.get('item')
    try:
        line_items,customer_info_dict,order_price,graphQL_id  = order_details_parser(item,v2=True)
        option_sku_lst = [collect_option_value(i["node"]['sku']) for i in line_items]
        item_check_dict = update_user_inventory_sale(line_items,user,check=True)
        line_items_2 = list(zip(option_sku_lst,line_items))
        return  line_items, line_items_2, customer_info_dict, order_price, item_check_dict, graphQL_id, item
    except:
        line_items, line_items_2, customer_info_dict, order_price, item_check_dict, graphQL_id, item = [],[], {}, "  Order has been fulfilled or canceled", {},"null","item"

        return line_items, line_items_2, customer_info_dict, order_price, item_check_dict, graphQL_id, item


#post handler for user order details page
def user_order_details_post_handler(user,item,graphQL_id,line_items,customer_info_dict,token, order_price):
    if list(request.form.keys())[0] == 'cashapp':
        response = cash_app_update(user,item)
        return 'cashapp',response
    if list(request.form.keys())[0] == 'sku':
        conn.execute(f"UPDATE {user}_orders SET completed='{datetime.datetime.now()}',fulfillment_status='FULFILLED' WHERE order_id='{item}'")
        conn.commit()
        update_user_inventory_sale(line_items,user)
        fulfill_order(graphQL_id,user)
        return 'sku',user,token
    if list(request.form.keys())[0] == 'name':
        eta = get_eta(customer_info_dict)
        send_canned_text(eta,customer_info_dict["name"], user, order_price )
        return "cannedtext",'<h1>Text Message Sent</h1>'
    if list(request.form.keys())[0] == 'route':
        lat , lng = customer_info_dict["latitude"], customer_info_dict["longitude"]
        return 'route',lat,lng




'''Shopify Unfulfilled Orders____________________________________________________________________'''


#collect data for todays orders from shopify
def collect_todays_order_data():
    raw_df = orders_api_call_1()
    #print(f"\n\nDF 1:{raw_df}\n\n")
    df = raw_df.loc[(raw_df["order_date"] == today_str) | (raw_df["order_date"] == yesterday_str) | (raw_df["order_date"] == tomorrow_str)][["order_ids","fulfillment_status","order_time_raw","name"]]
    #print(f"\n\nDF 2:{df}\n\n")
    df = check_for_claimed(df)
    return df

#post handler for order details page
def order_page_post_handler(user,token):
        item = request.form["item"]
        return item


'''Details for Order (shopify)___________________________________________________________________'''


#collect data for orders details page
def collect_orders_details_page_data(user):
    item = request.args.get('item')
    raw_df,line_items,customer_info_dict,order_price = order_details_parser(item) #,graphQL_id
    item_check_dict = update_user_inventory_sale(line_items,user,check=True)
    option_sku_lst = [collect_option_value(i["node"]['sku']) for i in line_items]
    line_items_2 = list(zip(option_sku_lst,line_items))
    return item, line_items_2, customer_info_dict, order_price, item_check_dict, raw_df


#post handler for orders details page
def orders_details_post_handler(raw_df,item,user,token):
    df = clean_orders_df(raw_df,item)
    df.to_sql(f"{user}_orders",con=conn, index=False, if_exists="append")
    conn.commit()
    df = pandas.read_sql(f"select * from {user}_orders",con=conn)
    return True


'''Admin Page____________________________________________________________________________________'''
#post handler for admin page
def admin_page_post_handler():
    if list(request.form.keys())[0] == 'users':
        response = driver_week_summary(f"{username}",[start_date,end_date])





'''system_funcions_______________________________________________________________________________'''

#collect usernames
def get_usernames():
    username_lst = pandas.read_sql("select username from users", con=conn).values.tolist()

    username_lst = [i[0] for i in username_lst]

    return username_lst

#last 20 unfulfilled orders then the first 20 items in each order
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

#variation of order_api_call function
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

#verify user has logged in
def verify_session(confirmed_session):
    try:
        token = request.args.get('token')
        user = request.args.get('user')
    except:
        return False, False
    try:
        if confirmed_session[user] == token:
            return user,token
        else:
            return False,False
    except:
        return False, False

#Collect items data
def items_data_call(update = False): 
    
    if update == True:
        os.system("rm products_export_1.csv")
        browser = Browser('firefox', executable_path="/usr/local/bin/geckodriver", headless=False)
        url = 'https://accounts.shopify.com/store-login'
        shop_domain = 'seni-society-delivery.myshopify.com'
        account_email = 'mr.robot7823465@gmail.com'
        account_password = '!Shopifysucks1'
        browser.visit(url)
        browser.find_by_id("shop_domain").fill(shop_domain)
        browser.find_by_name("commit").click()
        browser.find_by_id("account_email").fill(account_email)
        time.sleep(6)
        browser.find_by_name("commit").click()
        browser.find_by_id("account_password").fill(account_password)
        browser.find_by_name("commit").click()
        time.sleep(6)
        browser.find_by_text('Products').click()
        browser.find_by_text('Export').click()
        time.sleep(60)
        browser.quit()
        os.system("mv ~/Downloads/products_export_1.csv .")
        raw_df = pandas.read_csv("products_export_1.csv")
        raw_df.to_sql("items_data",con=conn, index=False, if_exists='replace')
    
    else:
        raw_df = pandas.read_csv("products_export_1.csv")
    
    

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
    inventory_df = raw_df[["Title","Variant-SKU","Variant-Inventory-Qty","Variant-Price"]]
    inventory_df.columns = ['display_name','sku','inventory_quantity','line_item_price']

    inventory_df.dropna(how="all",inplace=True)

    return inventory_df

#create new user and related tables
def create_user():
    os.system("clear")
    username = input("Enter desired username:\n")
    os.system("clear")
    password = stdiomask.getpass(prompt="enter desired password:\n", mask="*")
    username_lst = get_usernames()
    #check to see if user exists
    if username in username_lst:
        return f"Aborted:\nUsername {username} already exists"
    os.system("clear")
    phone_number = input("enter phone number:\n")
    new_user_df = items_data_call()
    #set inventory to 0
    new_user_df["inventory_quantity"] = 0
    
    password = hash_function(password)

    conn.execute(f'INSERT INTO users (username, hash_key, phone_number) VALUES ("{username}","{password}","{phone_number}")')
    conn.commit()

    new_user_df.to_sql(f'{username}',con=conn,if_exists="fail",index=False)

    new_user_orders_df = pandas.DataFrame(columns=["order_id","fulfillment_status","line_items","order_time_raw","order_date","customer_data","order_price","customer_names","accepted","completed","paid_with_cash_app"])
    new_user_orders_df.to_sql(f'{username}_orders',con=conn,index=False,if_exists="fail")
  
#clear session function
def reset_shopify_session():
    shopify.ShopifyResource.clear_session()
    session = shopify.Session("https://seni-society-delivery.myshopify.com",'2020-10',access_token)
    shopify.ShopifyResource.activate_session(session)
    return True


#parseing data for incoming orders df
def clean_orders_df(raw_df,item):
    raw_df = raw_df.copy()
    df = raw_df.loc[raw_df.order_id == item]
    df["line_items"] = df["line_items"].astype('str')
    df["customer_data"] = df["customer_data"].astype('str')
    df["accepted"] = datetime.datetime.now()
    df["completed"] = None 
    return df

#paresing data for specified order
def order_details_parser(item,v2=False):
    raw_df = orders_api_call()
    line_items = raw_df.loc[raw_df.order_id == item]["line_items"].item()
    customer_info_dict = raw_df.loc[raw_df.order_id == item]["customer_data"].item()
    customer_info_dict.pop("id")
    order_price = raw_df.loc[raw_df.order_id == item]["order_price"].item()
    if v2 == True:
        graphQL_id = raw_df.loc[raw_df.order_id == item]["shopify_id"].item()
        return line_items,customer_info_dict,order_price,graphQL_id


    return raw_df,line_items,customer_info_dict,order_price

#send canned text to sebastian
def send_canned_text(eta,customer_name,user,delivery_total):
    user_df = pandas.read_sql("select * from users",con=conn)
    user_phone_number = user_df.loc[user_df.username == user,"phone_number"].item()
    message_to_send = f'''ETA {eta} \nHello {customer_name} !  This is {user} with The Sensi Society\nDelivery Total {delivery_total} cash or cash app\nPayments accepted via cash or Cash App: {float(delivery_total) + 5.00} (+$5) Send to $SensiSociety\nDelivery drivers don’t carry change for safety purposes.\nPlease have ID READY upon delivery.\n🙏\nPS: HONESTLY the biggest help you can do is writing a review for us :)\nhttps://g.page/higher-ground-delivery/review?gm\nThank you so much for your order!\nNeed to Order again?\nLive Menu: TheSensiSociety.com'''
    client.messages.create(from_=twilio_config.MY_FIRST_TWILIO_NUMBER, to=user_phone_number, body=message_to_send)

#fufill and mark as paid on shopify
def fulfill_order(shopify_order_id,user):
    #just for me:
    if user == "sebastian":
        user = "Seb"
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

    #add username tag to order 'tags'
    shopify.GraphQL().execute('''
        mutation {
            tagsAdd(id: "'''+shopify_order_id+'''", tags: ["'''+user+'''"]) {
            node {
                id
            }
            userErrors {
                field
                message
            }
        }


    }''')
    
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
                    new_dict[df.loc[df.sku == i, "display_name"].item()] = "False"
            elif i not in df.sku.tolist():
                new_dict["VARIANT"] = "sku has no Title"
        return new_dict
                

    
    
    for i in sku_quantity_dict:
        if i in df.sku.tolist():
            quantity = sku_quantity_dict[i]
            df.loc[df.sku == i, "inventory_quantity"] -= quantity
    return df.to_sql(f"{user}", con=conn, index=False, if_exists="replace")

#takes username and date range (query one day after specified date) return summary df 
def driver_week_summary(username,dates):
    #last date must be a monday
    df = pandas.read_sql(f"select * from {username}_orders",con=conn)
    df.paid_with_cash_app.fillna(0.0,inplace=True)
    df.paid_with_cash_app = df.paid_with_cash_app.apply(lambda x: float(x))
    df = df.loc[(pandas.to_datetime(df.completed) > pandas.to_datetime(dates[0])) & (pandas.to_datetime(df.completed) < pandas.to_datetime(dates[1])) & (df.fulfillment_status == "FULFILLED")]

    driver_estimate_pay = df.order_price.count() * 15
    total_money_brought_in = df.loc[df.paid_with_cash_app < 1, "order_price"].sum()
    paid_with_cash_app_lst = df.paid_with_cash_app.apply(lambda x: "CASH APP" if x == 1  else "COD").tolist()
    total_orders_delivered = df.completed.count()
    print(f"Estimate Pay:\t\t\t{driver_estimate_pay}\nTotal Collected:\t\t{total_money_brought_in}\nOrders Delivered:\t\t{total_orders_delivered}\n")
    print(f"Orders for {dates[0]} to {dates[1]}:")
    for i in range(len(df.completed.tolist())):
        print("\t","CUSTOMER",df.customer_names.tolist()[i],"\n\t ORDER PRICE",df.order_price.tolist()[i],"\n\t","TIMESTAMP",df.completed.tolist()[i],"\n\t","PAYMENT METHOD",paid_with_cash_app_lst[i],"\n")

    return df

#check user for missing skus
def check_for_new_items(user):
    inventory_df = items_data_call()
    user_inventory = pandas.read_sql(f"select * from {user}", con=conn)
    lst_tups = list(zip(inventory_df.display_name.tolist(),inventory_df.sku.tolist()))
    lst_tups2 = list(zip(user_inventory.display_name.tolist(),user_inventory.sku.tolist()))
    return [i for i in lst_tups if i not in lst_tups2 and type(i[0]) == float and type(i[1]) == str]

#check the option value of a given sku
def collect_option_value(sku):
    df = pandas.read_sql("select * from items_data",con=conn)
    try:
        option_sku_value = df.loc[df["Variant SKU"] == sku,'Option1 Value'].item()
    except:
        option_sku_value = "Tip"


    return option_sku_value

#collect coordinates for all customers in USER orders
def order_coords(user):
    df = pandas.read_sql(f"select * from {user}_orders",con=conn)
    customer_data = [ (json.loads(i.replace(r"'" ,r'"' ))["latitude"], json.loads(i.replace(r"'" ,r'"' ))["longitude"]) for i in df.loc[df.fulfillment_status == "UNFULFILLED", "customer_data"].tolist()]

    customer_data.sort()
    
    lat_and_lng = [{'lat':i,'lng':v} for i,v in customer_data]

    lat = lat_and_lng[-1]['lat']

    lng = lat_and_lng[-1]['lng']
    
    return lat,lng,lat_and_lng

#collect the eta for a given customer
def get_eta(customer_info_dict):
    lat, lng = customer_info_dict["latitude"],customer_info_dict["longitude"]
    response = requests.get(f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving&dir_action=navigate")
    eta = re.search(r"You should arrive around.*",response.text).group().split(".")[0].replace("You should arrive around","")
    return eta

#check for any claimed orders
def check_for_claimed(df):
    users = pandas.read_sql("select * from users", con=conn)
    order_lst = df.order_ids.tolist()
    df_lst = []
    for i in users.username.tolist():
        if i != "admin":
            df_user_orders = pandas.read_sql(f"select * from {i}_orders",con=conn)
            df_lst.append(df_user_orders)
    user_claimed_lst = []
    for i in df_lst:
        for i in i.order_id:
            user_claimed_lst.append(i)
    for i in order_lst:
        if i in user_claimed_lst:
            df.drop(df.loc[df.order_ids == i].index,inplace = True)
    return df

#mark order as paid with cash app
def cash_app_update(user,item):
    user_orders_df = pandas.read_sql(f"select * from {user}_orders",con=conn)
    if user_orders_df.loc[user_orders_df.order_id == item, "paid_with_cash_app"].item() == 1:
        user_orders_df.loc[user_orders_df.order_id == item, "paid_with_cash_app"] = None
        user_orders_df.to_sql(f"{user}_orders",if_exists='replace',con=conn,index=False)
        return "<h1>Marked as Cash</h1>"
    user_orders_df.loc[user_orders_df.order_id == item, "paid_with_cash_app"] = True
    user_orders_df.to_sql(f"{user}_orders",if_exists='replace',con=conn,index=False)
    return "<h1>Marked with CashAPP</h1>"