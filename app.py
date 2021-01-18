from parsedata import *

app = Flask(__name__)

run_with_ngrok(app)

nav = Nav(app)

admin_session = {}
confirmed_session = {}


#Favicon Directory
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path,'favicon_io'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

#Favicon Directory
@app.route('/apple-touch-icon-120x120-precomposed.png')
def favicon_apple120_pre():
    return send_from_directory(os.path.join(app.root_path,'favicon_io'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

#Favicon Directory
@app.route('/apple-touch-icon-120x120.png')
def favicon_apple120():
    return send_from_directory(os.path.join(app.root_path,'favicon_io'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

#Favicon Directory
@app.route('/apple-touch-icon-precomposed.png')
def favicon_apple_pre():
    return send_from_directory(os.path.join(app.root_path,'favicon_io'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

#Favicon Directory
@app.route('apple-touch-icon.png')
def apple_touch_icon():
    return send_from_directory(os.path.join(app.root_path,'favicon_io'), 'apple-touch-icon.png', mimetype='image/vnd.microsoft.icon')



#Nav Bar
@nav.navigation('nav_bar')
def create_navbar():
    inventory_view = View('Inventory', 'driver_inventory',user=request.args.get('user'),token=request.args.get('token'))
    orders_view = View('Unfulfilled Orders','order_page',user=request.args.get('user'), token=request.args.get('token'))
    user_orders = View('User Orders','user_orders',user=request.args.get('user'), token=request.args.get('token'))
    logout = View('Logout','login_page',user=request.args.get('user'), token=request.args.get('token'))
    return Navbar('Mysite', inventory_view, orders_view, user_orders, logout)

#Login Page
@app.route("/", methods=['GET','POST'])
def login_page():
    render_template("driver_login.html")
    if request.method == "POST":
        response = login_page_verification(confirmed_session)
        if response == False:
            return "<h1>Invalid Creds</h1>"
        if response[0] == 'user':
            return redirect(url_for("driver_inventory",user=response[1],token=response[2],code=302,response=200,_scheme="https",_external=True))
        if response[0] == 'admin':
            return redirect(url_for("admin_page",user=response[1],token=response[2],code=302,response=200,_scheme="https",_external=True))
    return render_template("driver_login.html")

#User Inventory
@app.route("/driver_inventory", methods=["GET","POST"])
def driver_inventory():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>Login in expired</h1>'
    df = pandas.read_sql(f"select * from {user}", con=conn)
    if request.method == "POST":
        item = request.form["item"]
        return redirect(url_for("item_details",user=user,item=item, token=token,code=302,response=200,_scheme="https",_external=True))

    return render_template("driver_inventory.html",df=df,user=user)

#Details on Inventory Item (USER)
@app.route("/description", methods=["GET","POST"])
def item_details():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>refresh session</h1>'
    df, sku, html_data, price, image = collect_items_details_data(user)
    if request.method == "POST":
        response = item_details_post_handler(user, sku, token)
        return redirect(url_for("driver_inventory",user=response[0],token=response[-1],code=302,response=200,_scheme="https",_external=True))

    return render_template("update_items.html",df=df,price=price,html_data=html_data,image=image)

#Orders for USER
@app.route("/user_orders", methods=['GET','POST'])
def user_orders():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>refresh session</h1>'
    if request.method == "POST":
        response = user_orders_post_handler(user,token)
        if response[0] == 'route':
            return render_template("routing_page.html",lat=response[1],lng=response[2],lst=response[3])
        if response[0] == 'item':
            return redirect(url_for('user_orders_details',user=user,token=token,item=response[1],code=302,response=200,_scheme="https",_external=True))
        if response[0] == "log":
            return response[1].to_html()
    df = collect_user_orders_data(user)
    return render_template("user_orders.html", user=user, df=df)

#Detials for Order (USER)
@app.route("/user_orders/details", methods=['GET','POST'])
def user_orders_details():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>refresh session</h1>'
    line_items, line_items_2, customer_info_dict, order_price, item_check_dict, graphQL_id, item = collect_user_order_details(user)
    if request.method == "POST":
        response = user_order_details_post_handler(user,item,graphQL_id,line_items,customer_info_dict,token, order_price)
        if response[0] == "cashapp":
            return response[1]
        if response[0] == "cannedtext":
            return response[1]
        if response[0] == "sku":
            return redirect(url_for("user_orders",user=response[1],token=response[2],code=302,response=200,_scheme="https",_external=True))
        if response[0] == 'route':
            return redirect(f"https://www.google.com/maps/dir/?api=1&destination={response[1]},{response[2]}&travelmode=driving&dir_action=navigate")

    return render_template("user_order_details.html",id=item , lst=line_items_2, dict1=customer_info_dict, order_price=order_price,item_check_dict=item_check_dict)

#Shopify Unfulfilled Orders
@app.route("/todays_orders",methods=["GET","POST"])
def order_page():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>refresh session</h1>'
    df = collect_todays_order_data()
    if request.method == "POST":
        item = order_page_post_handler(user,token)
        return redirect(url_for("order_details",user=user,token=token, item=item,code=302,response=200,_scheme="https",_external=True))
    return render_template('todays_orders.html',df=df)

#Details for Order (shopify)
@app.route("/todays_orders/order_details",methods=["GET","POST"])
def order_details():
    user, token = verify_session(confirmed_session)
    if user == False or token == False:
        return '<h1>refresh session</h1>'
    item, line_items_2, customer_info_dict, order_price, item_check_dict, raw_df = collect_orders_details_page_data(user)
    if request.method == "POST":
        orders_details_post_handler(raw_df,item,user,token)
        return redirect(url_for("user_orders",user=user,token=token,code=302,response=200,_scheme="https",_external=True))

    return render_template("orders_details.html",id=item , lst=line_items_2, dict1=customer_info_dict, order_price=order_price, item_check_dict=item_check_dict)

#Admin Page
@app.route("/admin_page")
def admin_page():
    df = pandas.read_sql("select * from sebastian_orders",con=conn)
    return df.to_html()

#install link
@app.route("/install",methods=['GET'])
def install():
    print("intalling...")
    return "install page"


if __name__ == "__main__":
   app.run()
