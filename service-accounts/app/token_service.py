import os
from flask import Flask, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__)

# Read credentials from environment variables
client_id = os.environ.get('AUTH0_CLIENT_ID')
client_secret = os.environ.get('AUTH0_CLIENT_SECRET')

if not client_id or not client_secret:
    raise ValueError("AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET must be set in environment variables.")

# Auth0 domain
domain = 'dev-jkxyxuthob0qc1nw.us.auth0.com'

# Your API identifier (audience)
api_identifier = 'https://auth.braingeneers.gi.ucsc.edu/'  # Replace with your actual API identifier

# Default expiration days
DEFAULT_EXPIRATION_DAYS = 120


@app.route('/generate_token', methods=['GET', 'POST'])
def generate_token():
    if request.method == 'POST':
        days = request.json.get('days', DEFAULT_EXPIRATION_DAYS) if request.json else DEFAULT_EXPIRATION_DAYS
    else:  # GET
        days = request.args.get('days', DEFAULT_EXPIRATION_DAYS, type=int)

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(days=days)
    expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')

    # Create a new token
    token_payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': api_identifier,
        'grant_type': 'client_credentials'
    }
    token_response = requests.post(f'https://{domain}/oauth/token', json=token_payload)

    if token_response.status_code == 200:
        token_data = token_response.json()
        return jsonify({
            'access_token': token_data['access_token'],
            'expires_at': expires_at_str
        })
    else:
        return jsonify({'error': 'Failed to generate token', 'details': token_response.text}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
