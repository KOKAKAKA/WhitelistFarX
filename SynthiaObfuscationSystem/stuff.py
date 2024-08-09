from flask import Flask, request, jsonify, Response
import os
import json
import uuid
import subprocess

app = Flask(__name__)

# Directory for saving pastes
PASTE_DIR = 'SavedPastes'
os.makedirs(PASTE_DIR, exist_ok=True)

@app.route('/paste', methods=['POST'])
def create_paste():
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'error': 'Content is required'}), 400
    
    paste_id = str(uuid.uuid4())
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')

    with open(paste_path, 'w') as f:
        json.dump({'content': data['content']}, f)
    
    return jsonify({'id': paste_id}), 201

@app.route('/paste/<paste_id>', methods=['GET'])
def get_paste(paste_id):
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')
    
    if not os.path.exists(paste_path):
        return jsonify({'error': 'Paste not found'}), 404

    with open(paste_path, 'r') as f:
        content = json.load(f)
    
    return jsonify({'content': content['content']})

@app.route('/paste/<paste_id>/raw', methods=['GET'])
def get_paste_raw(paste_id):
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')
    
    if not os.path.exists(paste_path):
        return jsonify({'error': 'Paste not found'}), 404

    with open(paste_path, 'r') as f:
        content = json.load(f)['content']

    lua_code = f"_ = [[Protected By Synthia V1]]\n\n{content}"

    response = Response(lua_code, mimetype='text/plain')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

@app.route('/obfuscate', methods=['POST'])
def obfuscate_lua_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'Code is required'}), 400

    lua_code = data['code']
    preset = data.get('preset', 'Medium')  # Default to Medium if preset is not provided
    lua_version = data.get('version', '')  # Default to empty if version is not provided

    # Write the Lua code to a temporary file
    temp_file_path = 'temp.lua'
    with open(temp_file_path, 'w') as file:
        file.write(lua_code)
    
    try:
        # Prepare the command
        command = ['lua', './Prometheus/cli.lua', '--preset', preset, temp_file_path]
        if lua_version == 'Lua51':
            command.append('--Lua51')
        elif lua_version == 'LuaU':
            command.append('--LuaU')
        
        # Run Prometheus CLI with the specified obfuscation preset
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
        
        # Read the obfuscated file
        obfuscated_file_path = temp_file_path.replace('.lua', '.obfuscated.lua')
        with open(obfuscated_file_path, 'r') as file:
            obfuscated_code = file.read()
    except FileNotFoundError:
        return jsonify({'error': 'Lua interpreter or Prometheus CLI not found'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Create a new paste with the obfuscated code
    paste_id = str(uuid.uuid4())
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')
    
    with open(paste_path, 'w') as f:
        json.dump({'content': obfuscated_code}, f)
    
    return jsonify({
        'paste_id': paste_id,
        'preset': preset,
        'version': lua_version
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
