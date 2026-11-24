"""Official-build account access. GPLv3 rights remain unaffected."""
from __future__ import annotations
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .license_public import API_URL, PUBLIC_KEY

TERMS_VERSION = '2026-11-24'

class AccountError(RuntimeError):
    pass

def un64(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))

def verify_license(token, public_key=PUBLIC_KEY, timestamp=None, last_seen=0):
    try:
        encoded, signature = token.split('.')
        Ed25519PublicKey.from_public_bytes(un64(public_key)).verify(un64(signature), encoded.encode('ascii'))
        payload = json.loads(un64(encoded))
        current = int(time.time()) if timestamp is None else timestamp
        if payload.get('v') != 1 or payload.get('product') != 'pdf2muse-windows':
            raise ValueError('Wrong product')
        if current + 300 < max(last_seen, payload['issued_at']):
            raise ValueError('Clock moved backwards')
        if current >= payload['valid_until']:
            raise ValueError('Online refresh required')
        if payload['plan'] not in ('trial', 'perpetual'):
            raise ValueError('Wrong plan')
        if payload['plan'] == 'trial' and current >= payload['trial_until']:
            raise ValueError('Trial expired')
        return payload
    except Exception as error:
        raise AccountError('请联网登录或刷新授权 / Please sign in online or refresh your license.') from error

class _Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

def _protect(data, decrypt=False):
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = _Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)

class AccountClient:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'PDF2Muse' / 'account.dat'
        self.state = {}
        if self.path.exists():
            try:
                self.state = json.loads(_protect(self.path.read_bytes(), True))
            except Exception:
                self.state = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_bytes(_protect(json.dumps(self.state).encode()))
        temporary.replace(self.path)

    def request(self, endpoint, body=None, method=None):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'User-Agent': 'PDF2Muse/0.3.0'}
        if self.state.get('token'):
            headers['Authorization'] = 'Bearer ' + self.state['token']
        request = urllib.request.Request(API_URL + '/v1/' + endpoint, headers=headers,
            data=None if body is None else json.dumps(body).encode(), method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            try:
                message = json.load(error).get('error', 'Account service error.')
            except Exception:
                message = 'Account service error.'
            if error.code == 401:
                self.state.pop('license', None)
                self.state.pop('token', None)
                self._save()
            raise AccountError(message) from error
        except (OSError, ValueError) as error:
            raise AccountError('无法连接账号服务，请检查网络 / Cannot reach the account service.') from error
        if 'license' in result:
            self.state.update({key: result[key] for key in ('license', 'user', 'plan', 'active', 'token') if key in result})
            self.state['last_seen'] = max(self.state.get('last_seen', 0), result.get('server_time', 0))
            self._save()
        return result

    def active(self):
        try:
            payload = verify_license(self.state.get('license', ''), last_seen=self.state.get('last_seen', 0))
            self.state['last_seen'] = max(self.state.get('last_seen', 0), int(time.time()))
            self._save()
            return payload
        except AccountError:
            return None

    def refresh(self):
        return self.request('me')

    def logout(self):
        try:
            self.request('logout', {})
        finally:
            self.state = {}
            self._save()
