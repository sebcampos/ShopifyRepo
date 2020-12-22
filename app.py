from flask import Flask, redirect, url_for, request, render_template, session
from flask_ngrok import run_with_ngrok
from parsedata import *

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

