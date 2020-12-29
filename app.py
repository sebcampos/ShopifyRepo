from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from flask_nav import Nav
from flask_nav.elements import Navbar, Subgroup, View
from parsedata import *
import random


app = Flask(__name__)

run_with_ngrok(app)

nav = Nav(app)

#TODO turn this into key value pair dictionary
token_lst = []
user_lst = []
admin_session = {"True":""}

@nav.navigation('nav_bar')
def create_navbar():
    inventory_view = View('Inventory', 'driver_inventory',user=request.args.get('user'),token=request.args.get('token'))
    orders_view = View('Unfulfilled Orders','order_page',user=request.args.get('user'), token=request.args.get('token'))
    user_orders = View('User Orders','user_orders',user=request.args.get('user'), token=request.args.get('token'))
    logout = View('Logout','login_page',user=request.args.get('user'), token=request.args.get('token'))
    return Navbar('Mysite', inventory_view, orders_view, user_orders, logout)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_data()
    verified = verify_webhook(data, request.headers.get('X-Shopify-Hmac-SHA256'))

@app.route("/user_orders", methods=['GET','POST'])
def user_orders():
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    if request.method == "POST":
        item = request.form["item"]
        return redirect(url_for('user_orders_details',user=user,token=token,item=item,code=302,response=200))
    df = pandas.read_sql(f"select * from {user}_orders",con=conn)
    html_df = df[["order_id","fulfillment_status","order_date","customer_names","accepted","completed"]]
    return render_template("user_orders.html", user=user, df=html_df)

@app.route("/user_orders/details", methods=['GET','POST'])
def user_orders_details():
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    item = request.args.get('item')
    try:
        raw_df,line_items,customer_info_dict,order_price = order_details_parser(item)
    except:
        line_items,customer_info_dict,order_price = [], {}, "fufilled"
    if request.method == "POST":
        conn.execute(f"UPDATE {user}_orders SET completed='{datetime.datetime.now()}',fulfillment_status='FULFILLED' WHERE order_id='{item}'")
        conn.commit()
        return redirect(url_for("user_orders",user=user,token=token,code=302,response=200))
    return render_template("user_order_details.html",id=item , lst=line_items, dict1=customer_info_dict, order_price=order_price)    
    
@app.route("/", methods=['GET','POST'])
def login_page():
    df = pandas.read_sql("select * from users", con=conn)
    username_lst = get_usernames()
    render_template("driver_login.html") 
    if request.method == "POST":
        #Cheking login credentials
        if request.form["name"] in username_lst and request.form["name"] != "admin" and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
            user = request.form["name"]
            token= "".join([str(random.randint(1,30)) for i in range(0,5)])
            token_lst.append(token)
            user_lst.append(user)
            print(token_lst)
            print(user_lst)
            return redirect(url_for("driver_inventory",user=user,token=token,code=302,response=200))
        elif request.form["name"] == 'admin' and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
            return admin_page(request.form["name"])
        return "<h1>Invalid credentials reload page<h1>"
    return render_template("driver_login.html") 
    

@app.route("/todays_orders",methods=["GET","POST"])
def order_page():
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    raw_df = orders_api_call_1()
    df = raw_df.loc[(raw_df["order_date"] == today_str) | (raw_df["order_date"] == yesterday_str) | (raw_df["order_date"] == tomorrow_str)][["order_ids","fulfillment_status","order_time_raw","name"]]
    #df = raw_df[["order_ids","fulfillment_status","order_time_raw","name"]]
    if request.method == "POST":
        item = request.form["item"]
        return redirect(url_for("order_details",user=user,token=token, item=item,code=302,response=200))
    return render_template('todays_orders.html',df=df)

@app.route("/todays_orders/order_details",methods=["GET","POST"])
def order_details():    
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    item = request.args.get('item')
    raw_df,line_items,customer_info_dict,order_price = order_details_parser(item)
    if request.method == "POST":
        df = clean_orders_df(raw_df,item)
        df.to_sql(f"{user}_orders",con=conn, index=False, if_exists="append")
        conn.commit()
        df = pandas.read_sql(f"select * from {user}_orders",con=conn)
        return redirect(url_for("user_orders",user=user,token=token,code=302,response=200))
    return render_template("orders_details.html",id=item , lst=line_items, dict1=customer_info_dict, order_price=order_price)


@app.route("/driver_inventory", methods=["GET","POST"])
def driver_inventory():
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    df = pandas.read_sql(f"select * from {user}", con=conn)
    df.drop("index",axis=1,inplace=True)
    if request.method == "POST":
        item = request.form["item"]
        return redirect(url_for("item_details",user=user,item=item, token=token,code=302,response=200))

    return render_template("driver_inventory.html",df=df,user=user)


@app.route("/admin_page")
def admin_page(user):
    return f" Admin Page: {user}"


@app.route("/description", methods=["GET","POST"])
def item_details():
    users_session = verify_session(token_lst,user_lst)
    if users_session == False:
        return '<h1>refresh session</h1>'
    user = users_session[0]
    token = users_session[1]
    item = request.args.get('item')
    df = pandas.read_sql(f"select * from {user} where display_name='{item}'", con=conn)
    if request.method == "POST":
        new_val = request.form["updateme"]
        conn.execute(f"UPDATE {user} SET inventory_quantity={new_val} WHERE display_name='{item}'")
        conn.commit()
        return redirect(url_for("driver_inventory",user=user,token=token,code=302,response=200))
    return render_template("update_items.html",df=df)


@app.route("/install",methods=['GET'])
def install():
    print("intalling...")
    return "install page"




if __name__ == "__main__":
   app.run()

