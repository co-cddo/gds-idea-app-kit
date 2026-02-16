import logging

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

REDIRECT_URL = "https://gds-idea.click/401.html"

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
