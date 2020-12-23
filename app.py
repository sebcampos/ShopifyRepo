from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from parsedata import *

app = Flask(__name__)
run_with_ngrok(app)


@app.route("/driver_page")
def testing_page(user):
    results='Testing Stage'
    df = pandas.read_sql(f"select * from {user}", con=conn)
    df.drop("index",axis=1,inplace=True)
    return render_template("welcome.html",df=df,user=user)


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
            return testing_page(request.form["name"])
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

