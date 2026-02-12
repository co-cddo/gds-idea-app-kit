import logging

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

app = FastAPI()
auth = FastAPIAuth(app)


# Health check endpoint for ECS/ALB (unprotected)
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Main route - protected by app-wide auth middleware
@app.get("/")
def index(request: Request):
    user = auth.get_current_user(request)

    return {
        "message": "You are Authorised!",
        "email": user.email,
        "oidc_claims": user.oidc_claims,
        "access_claims": user.access_claims,
    }


# Additional example route - also automatically protected
@app.get("/api/user")
def get_user(request: Request):
    user = auth.get_current_user(request)

    return {"email": user.email, "groups": user.groups if hasattr(user, "groups") else []}
