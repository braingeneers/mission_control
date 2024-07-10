import os
from flask import Flask, request, jsonify
import requests
import configparser
from datetime import datetime, timedelta

app = Flask(__name__)

# Read credentials from environment variables or ~/.aws/credentials
client_id = os.environ.get('AUTH0_CLIENT_ID')
client_secret = os.environ.get('AUTH0_CLIENT_SECRET')

if not client_id or not client_secret:
    raise ValueError("AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET must be set in environment variables.")

# Auth0 domain
domain = 'dev-jkxyxuthob0qc1nw.us.auth0.com'


def get_management_token():
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': f'https://{domain}/api/v2/',
        'grant_type': 'client_credentials'
    }
    response = requests.post(f'https://{domain}/oauth/token', json=payload)
    return response.json()['access_token']


@app.route('/generate_token', methods=['GET'])
def generate_token():
    # 120 days = 4 months, braingeneerspy auto refreshes tokens every 1 month,
    # so the application must be activated at least once per 3 months
    days = request.json.get('days', 120)

    # Get management API token
    mgmt_token = get_management_token()

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(days=days)
    expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')

    # Create a new client grant
    headers = {
        'Authorization': f'Bearer {mgmt_token}',
        'Content-Type': 'application/json'
    }
    grant_payload = {
        'client_id': client_id,
        'audience': f'https://{domain}/api/v2/',
        'scope': []
    }
    requests.post(f'https://{domain}/api/v2/client-grants', json=grant_payload, headers=headers)

    # Create a new token
    token_payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': f'https://{domain}/api/v2/',
        'grant_type': 'client_credentials',
        'expires_in': days * 86400  # Convert days to seconds
    }
    token_response = requests.post(f'https://{domain}/oauth/token', json=token_payload)

    if token_response.status_code == 200:
        token_data = token_response.json()
        return jsonify({
            'access_token': token_data['access_token'],
            'expires_at': expires_at_str
        })
    else:
        return jsonify({'error': 'Failed to generate token'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
