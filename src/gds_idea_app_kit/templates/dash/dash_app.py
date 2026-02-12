import json
import logging

from cognito_auth.dash import DashAuth
from dash import Dash, Input, Output, dcc, html
from flask import jsonify, request

# Configure logging - quiet noisy libraries
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Quiet noisy third-party loggers
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)  # Flask logger

# Your app logger
logger = logging.getLogger(__name__)

REDIRECT_URL = "https://gds-idea.click/401.html"

app = Dash(__name__)


# create the health check endpoint for the ALB
@app.server.before_request
def maybe_handle_health():
    if request.path == "/health":
        return jsonify({"status": "ok"}), 200


auth = DashAuth()
auth.protect_app(app)  # protects the entire app.


# Layout with dynamic content that will be populated by callback
app.layout = html.Div(
    [
        html.H1("You are Authorised!"),
        html.Div(id="user-info"),
        # Hidden interval to trigger initial load
        dcc.Interval(id="interval", interval=1000, n_intervals=0, max_intervals=1),
    ]
)


# Callback to fetch and display user info within app context
@app.callback(Output("user-info", "children"), Input("interval", "n_intervals"))
def display_user_info(n):
    user = auth.get_auth_user()

    return html.Div(
        [
            html.P(f"Welcome {user.email}"),
            html.H2("OIDC Claims:"),
            html.Pre(json.dumps(user.oidc_claims, indent=2)),
            html.H2("Access Claims:"),
            html.Pre(json.dumps(user.access_claims, indent=2)),
        ]
    )


# Expose server for gunicorn (production)
server = app.server

if __name__ == "__main__":
    # Development mode: run Flask dev server with auto-reload
    app.run(debug=True, host="0.0.0.0", port=8080)
