from flask import Flask, render_template, request, redirect, Response
from flask_ngrok import run_with_ngrok
from flask_sqlalchemy import SQLAlchemy
from config import Config as cfg
import requests
import json 

app = Flask(__name__)
app.debug = True
app.secret_key = cfg.SECRET_KEY
run_with_ngrok(app)

@app.route("/")
def login_page():
    return render_template("driver_login.html")

@app.route("/install",methods=['GET'])
def install():
    #Connect to a shopify store
    if request.args.get('shop'):
        shop = request.args.get('shop')
    else:
        return Response(response="Error:parameter shop not found", status=500)
    
    auth_url = f"https://{shop}/admin/oauth/authorize?client_id={cfg.SHOPIFY_CONFIG['API_KEY']}&scope={cfg.SHOPIFY_CONFIG['SCOPE']}&redirect_uri={cfg.SHOPIFY_CONFIG['REDIRECT_URI']}"
    
    print("Debug - auth URL: ",auth_url)
    return redirect(auth_url)

@app.route("/connect",methods=['GET'])
def connect():
    if request.args.get("shop"):
        params = {
            "client_id": cfg.SHOPIFY_CONFIG["API_KEY"],
            "client_secret": cfg.SHOPIFY_CONFIG["API_SECRET"],
            "code":request.arg.args.get("code")
        }
        resp = requests.post(f"https://{request.args.get('shop')}/admin/oauth/access_token", data=params)

        if 200 == resp.status_code:
            resp_json = json.loads(resp.text)
            return render_template('welcome.html') 
        else:
            print("Failed to get access token: ",resp.status_code, resp.text)
            return "error"
if __name__ == "__main__":
   app.run()
