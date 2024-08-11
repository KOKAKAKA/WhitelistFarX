from flask import Flask, request, redirect, session, url_for
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Replace these values with your actual credentials
CLIENT_ID = '1271690853064245380'
CLIENT_SECRET = 'yhy6D1X6u0_-I12okZ4Vd-q8bjBWLuvV'
REDIRECT_URI = 'http://localhost:5000/callback'
TOKEN_URL = 'https://discord.com/api/oauth2/token'
USER_URL = 'https://discord.com/api/v10/users/@me'

@app.route('/')
def home():
    if 'access_token' in session:
        return redirect(url_for('check_server'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return redirect(f'https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('login'))
    
    token_response = requests.post(TOKEN_URL, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify guilds'
    })
    
    token_response_data = token_response.json()
    if 'access_token' not in token_response_data:
        return redirect(url_for('login'))
    
    session['access_token'] = token_response_data['access_token']
    return redirect(url_for('check_server'))

@app.route('/check_server')
def check_server():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))
    
    TARGET_SERVER_ID = '1253670424345051146'

    user_guilds_response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers={
        'Authorization': f'Bearer {access_token}'
    })
    
    if user_guilds_response.status_code == 200:
        guilds = user_guilds_response.json()
        is_in_server = any(guild['id'] == TARGET_SERVER_ID for guild in guilds)
        if is_in_server:
            return 'Yes'
        else:
            return 'No'
    else:
        return 'Error fetching guilds', 500

if __name__ == '__main__':
    app.run(debug=True)
