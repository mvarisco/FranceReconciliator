import base64
import hashlib
import os
import secrets
import ssl
import threading
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import config


def generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("utf-8")


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def generate_self_signed_cert(cert_file: str, key_file: str) -> None:
    """Generate a self-signed certificate for HTTPS localhost callback."""
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return
    
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from datetime import datetime, timedelta
    import ipaddress
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Local"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"127.0.0.1"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.DNSName(u"127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))


class HTTPSServer(HTTPServer):
    """HTTPS version of HTTPServer."""
    def __init__(self, host_port, handler, cert_file, key_file):
        super().__init__(host_port, handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        self.socket = context.wrap_socket(self.socket, server_side=True)



class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server_version = "OCIAuth/1.0"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [None])[0]
        self.server.auth_state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication Completed</h1><p>You can return to the application.</p></body></html>"
        )

    def log_message(self, format, *args):
        return


class AuthWorker(QObject):
    log_signal = Signal(str)
    result_signal = Signal(str)
    finished = Signal()

    def __init__(self, supplier_code: str):
        super().__init__()
        self.supplier_code = supplier_code

    def run(self):
        try:
            self.log_signal.emit("Generating PKCE and opening browser...")
            code_verifier = generate_code_verifier()
            code_challenge = generate_code_challenge(code_verifier)
            state = secrets.token_urlsafe(16)

            auth_url = (
                f"{config.AUTHORIZATION_ENDPOINT}?response_type=code"
                f"&client_id={urllib.parse.quote(config.CLIENT_ID)}"
                f"&redirect_uri={urllib.parse.quote(config.REDIRECT_URI)}"
                f"&scope={urllib.parse.quote(config.SCOPES)}"
                f"&code_challenge={urllib.parse.quote(code_challenge)}"
                f"&code_challenge_method=S256"
                f"&state={urllib.parse.quote(state)}"
            )

            webbrowser.open(auth_url)

            parsed_redirect = urllib.parse.urlparse(config.REDIRECT_URI)
            if parsed_redirect.scheme.lower() != "https":
                self.log_signal.emit(
                    f"REDIRECT_URI must be HTTPS local for the listener: {config.REDIRECT_URI}"
                )
                self.finished.emit()
                return

            callback_host = parsed_redirect.hostname or "127.0.0.1"
            callback_port = parsed_redirect.port or 8000
            callback_path = parsed_redirect.path
            if callback_path != "/callback":
                self.log_signal.emit("REDIRECT_URI must end with /callback.")
                self.finished.emit()
                return

            # Generate self-signed certificate for HTTPS
            cert_file = os.path.join(os.path.expanduser("~"), ".oauth_localhost.crt")
            key_file = os.path.join(os.path.expanduser("~"), ".oauth_localhost.key")
            generate_self_signed_cert(cert_file, key_file)
            
            server = HTTPSServer((callback_host, callback_port), OAuthCallbackHandler, cert_file, key_file)
            server.auth_code = None
            server.auth_state = None

            self.log_signal.emit(
                f"Waiting for authentication redirect on {callback_host}:{callback_port}{callback_path}..."
            )
            while server.auth_code is None:
                server.handle_request()

            if server.auth_state != state:
                self.log_signal.emit("Error: state value does not match.")
                self.finished.emit()
                return

            self.log_signal.emit("Exchanging authorization code for access token...")
            token_data = {
                "grant_type": "authorization_code",
                "code": server.auth_code,
                "redirect_uri": config.REDIRECT_URI,
                "client_id": config.CLIENT_ID,
                "code_verifier": code_verifier,
            }

            token_response = requests.post(config.TOKEN_ENDPOINT, data=token_data, verify=config.VERIFY_SSL)
            if token_response.status_code != 200:
                self.log_signal.emit(
                    f"Token error: {token_response.status_code} - {token_response.text}"
                )
                self.finished.emit()
                return

            tokens = token_response.json()
            access_token = tokens.get("access_token")
            if not access_token:
                self.log_signal.emit("Access token not found in response.")
                self.finished.emit()
                return

            self.log_signal.emit("Access token obtained, querying supplier API...")
            print("Access token:", access_token)
            supplier_description = self.lookup_supplier(access_token)
            self.result_signal.emit(supplier_description)
        except Exception as exc:
            self.log_signal.emit(f"Unexpected error: {exc}")
        finally:
            self.finished.emit()

    def lookup_supplier(self, access_token: str) -> str:
        url = f"{config.API_BASE_URL}{config.SUPPLIER_LOOKUP_PATH}?q=SupplierNumber={self.supplier_code}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers, verify=config.VERIFY_SSL)
        print("URL richiesta:", response.url)

        if response.status_code != 200:
            return f"Supplier API error: {response.status_code} - {response.text}"

        try:
            data = response.json()
        except ValueError:
            return f"Invalid API response: {response.text}"

        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            return f"No supplier found for code {self.supplier_code}."

        first_item = items[0]
        supplier_name = first_item.get("Supplier")
        if not supplier_name:
            return f"API response OK but Supplier field not found: {first_item}"

        return supplier_name


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCI OAuth Supplier Lookup")
        self.resize(600, 320)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Enter supplier code")

        self.lookup_button = QPushButton("Start OAuth and Search Supplier")
        self.lookup_button.clicked.connect(self.on_lookup_clicked)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("Operation status and messages...")

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Supplier description..." )

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Supplier Code:"))
        top_layout.addWidget(self.code_input)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.lookup_button)
        layout.addWidget(QLabel("Operation Log:"))
        layout.addWidget(self.status_text)
        layout.addWidget(QLabel("Supplier Description:"))
        layout.addWidget(self.result_text)
        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def append_log(self, text: str):
        self.status_text.append(text)

    def set_result(self, text: str):
        self.result_text.setPlainText(text)

    def on_lookup_clicked(self):
        supplier_code = self.code_input.text().strip()
        if not supplier_code:
            self.append_log("Enter a supplier code before starting.")
            return

        self.lookup_button.setEnabled(False)
        self.status_text.clear()
        self.result_text.clear()

        self.worker = AuthWorker(supplier_code)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.worker.log_signal.connect(self.append_log)
        self.worker.result_signal.connect(self.set_result)
        self.worker.finished.connect(self.on_worker_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_worker_finished(self):
        self.lookup_button.setEnabled(True)
        self.append_log("Operation completed.")
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
