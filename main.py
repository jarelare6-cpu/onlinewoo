from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import tempfile
import json
import requests

app = Flask(__name__)
CORS(app)

def run_code(code, timeout=30):
    """تشغيل كود Python في بيئة معزولة"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        # استبدال msvcrt بديل بسيط للمتصفح
        code = code.replace('import msvcrt', '# msvcrt not available on Linux')
        code = code.replace('msvcrt.getch()', 'b" "')
        f.write(code)
        tmpfile = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmpfile],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'stdout': '',
            'stderr': f'⏱ انتهت المهلة بعد {timeout} ثانية',
            'returncode': -1
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }
    finally:
        os.unlink(tmpfile)


def install_package(package):
    """تثبيت مكتبة pip"""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', package, '--quiet'],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return {'success': True, 'message': f'✅ تم تثبيت {package}'}
        else:
            return {'success': False, 'message': result.stderr}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': '⏱ انتهت المهلة'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': '🐍 Pharaoh Python Server is running!'})


@app.route('/run', methods=['POST'])
def run():
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No code provided'}), 400
    result = run_code(data['code'], timeout=data.get('timeout', 30))
    return jsonify(result)


@app.route('/pip', methods=['POST'])
def pip_install():
    data = request.get_json()
    if not data or 'package' not in data:
        return jsonify({'error': 'No package provided'}), 400
    result = install_package(data['package'])
    return jsonify(result)


@app.route('/pip/list', methods=['GET'])
def pip_list():
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            capture_output=True, text=True
        )
        packages = json.loads(result.stdout)
        return jsonify({'packages': packages})
    except:
        return jsonify({'packages': []})


# ═══ مسار البروكسي الجديد لاستقبال أحداث الألعاب وتمريرها وتخطي الـ CORS ═══
@app.route('/api/send-event', methods=['POST'])
def proxy_send_event():
    data = request.get_json()
    if not data or 'package' not in data or 'dev_key' not in data or 'body' not in data:
        return jsonify({'success': False, 'error': 'Missing raw payload fields'}), 400

    package = data['package']
    dev_key = data['dev_key']
    body_data = data['body']

    url = f"https://api2.appsflyer.com/inappevent/{package}"
    headers = {
        "Content-Type": "application/json",
        "authentication": dev_key
    }

    try:
        response = requests.post(url, headers=headers, json=body_data, timeout=15)
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'response': response.text
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
