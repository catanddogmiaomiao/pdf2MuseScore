import base64
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pdf2muse.licensing import AccountClient, AccountError, verify_license

def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

class LicenseTests(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
        self.public=b64(self.key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
        self.payload={'v':1,'product':'pdf2muse-windows','plan':'trial','issued_at':1000,'trial_until':2000,'valid_until':1800}

    def token(self):
        payload=b64(json.dumps(self.payload).encode())
        return payload+'.'+b64(self.key.sign(payload.encode()))

    def test_signed_trial_expiration_tampering_and_clock_rollback(self):
        token=self.token()
        self.assertEqual(verify_license(token,self.public,1500)['plan'],'trial')
        for current,seen in ((1800,0),(999,1500),(600,0)):
            with self.assertRaises(AccountError): verify_license(token,self.public,current,seen)
        modified=b64(json.dumps(dict(self.payload,plan='perpetual')).encode())+'.'+token.split('.')[1]
        with self.assertRaises(AccountError):verify_license(modified,self.public,1500)

    def test_dpapi_roundtrip_and_no_plaintext(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'account.dat'
            client=AccountClient(path)
            client.state={'token':'secret_session_token','license':'not-a-valid-license'}
            client._save()
            self.assertNotIn(b'secret_session_token',path.read_bytes())
            self.assertEqual(AccountClient(path).state,client.state)
            self.assertIsNone(client.active())
