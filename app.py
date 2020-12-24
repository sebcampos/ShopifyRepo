from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from flask_nav import Nav
from flask_nav.elements import Navbar, Subgroup, View
from parsedata import *

app = Flask(__name__)

run_with_ngrok(app)

nav = Nav(app)

global user
user = ""


@nav.navigation('nav_bar')
def create_navbar():
    inventory_view = View('Inventory', 'driver_inventory')
    orders_view = View('Unfulfilled Orders','order_page')

    return Navbar('Mysite', inventory_view, orders_view)


@app.route("/todays_orders")
def order_page():
    return render_template('todays_orders.html')


@app.route("/driver_inventory", methods=['GET','POST'])
def driver_inventory():
    global user
    if user == "":
        return "Invalid request"
    df = pandas.read_sql(f"select * from {user}", con=conn)
    df.drop("index",axis=1,inplace=True)
    return render_template("driver_inventory.html",df=df,user=user)



@app.route("/admin_page")
def admin_page(user):
    return f"{user}"

@app.route("/connect", methods=['GET','POST'])
def login_page():
    df = pandas.read_sql("select * from users", con=conn)
    username_lst = get_usernames()
    render_template("driver_login.html") 
    if request.method == "POST":
        #Cheking login credentials
        if request.form["name"] in username_lst and request.form["name"] != "admin" and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
            global user
            user = request.form["name"]
            return driver_inventory()
        elif request.form["name"] == 'admin' and request.form["password"] == hash_function(df.loc[df["username"] == request.form["name"]].values.tolist()[0][1],unhash=True):
            return admin_page(request.form["name"])
        return "<h1>Invalid credentials reload page<h1>"
    return render_template("driver_login.html") 

@app.route("/install",methods=['GET'])
def install():
    print("intalling...")
    return "install page"




if __name__ == "__main__":
   app.run()

