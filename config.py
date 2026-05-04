# Configuration for the OCI OAuth and supplier lookup API.

# OCI Public Client (Mobile Application) client ID
CLIENT_ID = "075c6d024eb04b58ae41ce7cba02e5cc"

# Your Oracle Identity Domain (OCI tenant domain name)
IDENTITY_DOMAIN = "idcs-4b9e5a0921d347fca67d5b9570b0cac7"

# The redirect URI registered in OCI for the Public Client.
# Deve essere un redirect locale HTTPS valido, ad esempio: https://127.0.0.1:8000/callback
REDIRECT_URI = "https://127.0.0.1:8000/callback"

# OAuth endpoints for OCI
AUTHORIZATION_ENDPOINT = f"https://{IDENTITY_DOMAIN}.identity.oraclecloud.com/oauth2/v1/authorize"
TOKEN_ENDPOINT = f"https://{IDENTITY_DOMAIN}.identity.oraclecloud.com/oauth2/v1/token"

# Scopes required for your API access. Add `openid` if needed.
SCOPES = "urn:opc:resource:fa:instanceid=687083897urn:opc:resource:consumer::all"

# API endpoint base URL to consume the supplier lookup service.
# Example: https://api.example.com
API_BASE_URL = "https://fa-efuf-dev25-saasfaprod1.fa.ocs.oraclecloud.com/fscmRestApi/resources/11.13.18.05"

# If the remote API uses a self-signed or otherwise untrusted certificate,
# set VERIFY_SSL to False to skip SSL certificate validation.
VERIFY_SSL = False

# Supplier lookup path. The app will call this endpoint with a supplier code.
SUPPLIER_LOOKUP_PATH = "/suppliers"

# If your supplier service expects a query parameter, the app will request:
#   {API_BASE_URL}{SUPPLIER_LOOKUP_PATH}?code=<supplier_code>
# If you need a different format, update the `supplier_lookup` function in main.py.
