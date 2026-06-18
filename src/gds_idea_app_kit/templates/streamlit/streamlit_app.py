import logging
import os
from pathlib import Path

import streamlit as st
from cognito_auth.streamlit import StreamlitAuth

# Configure logging - quiet noisy libraries
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Quiet noisy third-party loggers
logging.getLogger("watchdog").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)

# Your app logger
logger = logging.getLogger(__name__)

if os.getenv("COGNITO_AUTH_DEV_MODE", "").lower() == "true" and not os.getenv(
    "COGNITO_AUTH_DEV_CONFIG"
):
    os.environ["COGNITO_AUTH_DEV_CONFIG"] = str(
        Path(__file__).resolve().parent.parent / "dev_mocks" / "dev_mock_user.json"
    )

auth = StreamlitAuth()

user = auth.get_auth_user()


st.write("You are Authorised!")
st.write(f"Welcome {user.email}")

st.write("OIDC_claims:")
st.json(user.oidc_claims)

st.write("Access Claims:")
st.json(user.access_claims)

st.write("All Headers:")
st.json(dict(st.context.headers))
