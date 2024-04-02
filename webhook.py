# app.py
from hashlib import sha256
from hmac import compare_digest, HMAC

import flask
import json
import subprocess
from dotenv import load_dotenv, find_dotenv
from flask_httpauth import HTTPTokenAuth
from flask import Flask, request, Response

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='Bearer')

tokens = {
    "secret-token-1": "john",
    "secret-token-2": "susan"
}
playbook_dir = "/etc/ansible/infrastructure"
inventory_dir = "/etc/ansible/infrastructure/inventories/staging"


@auth.verify_token
def verify_token(token):
    if token in tokens:
        return tokens[token]


@app.route('/webhook', methods=['POST'])
@auth.login_required
def webhook():
    if request.method == 'POST':
        # Get JSON
        received_data = request.json
        # Convert JSON to String
        received_data_str = json.dumps(received_data)
        # Parse received_data_str
        parse_received_data_str = json.loads(received_data_str)
        # Formatting path to vars
        playbook_name = parse_received_data_str["playbook"]
        inventory_name = parse_received_data_str["inventory"]

        _playbook = f"{playbook_dir}/{playbook_name}"
        _inventory = f"{inventory_dir}/{inventory_name}"

        @flask.after_this_request
        def close_action(response):
            @response.call_on_close
            def run_playbook(inventory=_inventory, playbook=_playbook):
                ansible = subprocess.run(["/usr/local/bin/ansible-playbook", "-i", inventory, playbook],
                                         shell=False, check=True,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         encoding='utf-8')
                if ansible.returncode == 0:
                    return True, ansible.stdout
                else:
                    return False, ansible.stderr

            return response
        return Response(status=405)


if __name__ == "__main__":
    app.run(host='10.78.37.218', port=8000)
