import logging
import os
from pathlib import Path

from cognito_auth.fastapi import FastAPIAuth
from fastapi import FastAPI, Request

# Configure logging - quiet noisy libraries
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Quiet noisy third-party loggers
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Uvicorn access logs

# Your app logger
logger = logging.getLogger(__name__)

if os.getenv("COGNITO_AUTH_DEV_MODE", "").lower() == "true" and not os.getenv(
    "COGNITO_AUTH_DEV_CONFIG"
):
    os.environ["COGNITO_AUTH_DEV_CONFIG"] = str(
        Path(__file__).resolve().parent.parent / "dev_mocks" / "dev_mock_user.json"
    )

app = FastAPI()
auth = FastAPIAuth()
auth.protect_app(app)


# Health check endpoint for ECS/ALB (unprotected)
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Main route - protected by app-wide auth middleware
@app.get("/")
def index(request: Request):
    user = auth.get_auth_user(request)

    return {
        "message": "You are Authorised!",
        "email": user.email,
        "oidc_claims": user.oidc_claims,
        "access_claims": user.access_claims,
    }


# Additional example route - also automatically protected
@app.get("/api/user")
def get_user(request: Request):
    user = auth.get_auth_user(request)

    return {"email": user.email, "groups": user.groups if hasattr(user, "groups") else []}
