import logging
from flask import Flask, request, jsonify, Response
import os
import json
import uuid
import subprocess

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Directory for saving pastes and logs
PASTE_DIR = 'SavedPastes'
LOG_DIR = 'ObfuscationLogs'
os.makedirs(PASTE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def check_lua_syntax(lua_code):
    try:
        # Write the Lua code to a temporary file for syntax checking
        syntax_check_file = 'temp_syntax_check.lua'
        with open(syntax_check_file, 'w') as file:
            file.write(lua_code)

        # Run Lua script and capture any syntax errors
        result = subprocess.run(['lua', syntax_check_file], capture_output=True, text=True)
        if result.returncode != 0:
            return result.stderr  # Return syntax error message

        return None  # No syntax errors
    finally:
        # Clean up temporary file
        if os.path.exists(syntax_check_file):
            os.remove(syntax_check_file)

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

@app.route('/download/<paste_id>', methods=['GET'])
def download_paste(paste_id):
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')
    
    if not os.path.exists(paste_path):
        return jsonify({'error': 'Paste not found'}), 404

    with open(paste_path, 'r') as f:
        content = json.load(f)['content']

    # Create a file-like object and send as a response
    return Response(content, mimetype='text/plain', headers={
        'Content-Disposition': f'attachment; filename={paste_id}.lua'
    })

@app.route('/obfuscate', methods=['POST'])
def obfuscate_lua_code():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'Code is required'}), 400

    lua_code = data['code']
    preset = data.get('preset', 'Medium')
    lua_version = data.get('version', '')

    paste_id = str(uuid.uuid4())
    log_file_path = os.path.join(LOG_DIR, f'{paste_id}.log')

    # Check Lua code syntax
    syntax_error = check_lua_syntax(lua_code)
    if syntax_error:
        logger.error(f"Lua syntax error: {syntax_error}")
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Lua syntax error: {syntax_error}")
        return jsonify({'error': 'Syntax error in Lua code', 'details': syntax_error}), 400

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

        # Log the command being run
        logger.debug(f"Obfuscating Script...")
        
        # Run Prometheus CLI with the specified obfuscation preset
        result = subprocess.run(command, capture_output=True, text=True)
        logger.debug(f"Obfuscation output: {result.stdout}")
        logger.debug(f"Command error output: {result.stderr}")
        
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Command: {' '.join(command)}\n")
            log_file.write(f"Output: {result.stdout}\n")
            log_file.write(f"Error: {result.stderr}\n")
        
        if result.returncode != 0:
            raise Exception(result.stderr)

        # Read the obfuscated file
        obfuscated_file_path = temp_file_path.replace('.lua', '.obfuscated.lua')
        with open(obfuscated_file_path, 'r') as file:
            obfuscated_code = file.read()
    except FileNotFoundError:
        logger.error('Lua interpreter or Prometheus CLI not found')
        with open(log_file_path, 'w') as log_file:
            log_file.write('Error: Lua interpreter or Prometheus CLI not found')
        return jsonify({'error': 'Lua interpreter or Prometheus CLI not found'}), 500
    except Exception as e:
        logger.error(f"Exception occurred: {str(e)}")
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

    # Create a new paste with the obfuscated code
    paste_path = os.path.join(PASTE_DIR, f'{paste_id}.json')

    with open(paste_path, 'w') as f:
        json.dump({'content': obfuscated_code}, f)

    return jsonify({
        'paste_id': paste_id,
        'preset': preset,
        'version': lua_version
    })

@app.route('/obfuscatelog', methods=['GET'])
def get_obfuscation_log():
    paste_id = request.args.get('paste_id')
    if not paste_id:
        return jsonify({'error': 'paste_id is required'}), 400
    
    log_file_path = os.path.join(LOG_DIR, f'{paste_id}.log')
    
    if not os.path.exists(log_file_path):
        return jsonify({'error': 'Log not found for the specified paste_id'}), 404

    with open(log_file_path, 'r') as log_file:
        log_content = log_file.read()

    return Response(log_content, mimetype='text/plain', headers={
        'Content-Disposition': f'attachment; filename={paste_id}.log'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
