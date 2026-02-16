"""Implementation of the provide-role command.

Runs on the host machine to provide AWS credentials to the dev container by
writing temporary credentials to .aws-dev/, which is volume-mounted into the
container via docker-compose.

Two modes:
1. Role assumption (default): assumes the container role from your current
   profile credentials via STS. Requires aws_role_arn in [tool.webapp.dev].
2. Pass-through: extracts and writes your current profile credentials directly.
   Used when --use-profile is given or no aws_role_arn is configured.

Usage:
    AWS_PROFILE=aws-dev idea-app provide-role
    AWS_PROFILE=aws-dev idea-app provide-role --use-profile
    AWS_PROFILE=aws-dev idea-app provide-role --duration 7200
"""

import os
import sys
import tomllib
from pathlib import Path

import boto3
import click
from botocore.exceptions import ClientError, NoCredentialsError

AWS_DEV_DIR = ".aws-dev"
CREDENTIALS_FILE = "credentials"
CONFIG_FILE = "config"
DEFAULT_REGION = "eu-west-2"


def _check_aws_profile() -> str:
    """Check that AWS_PROFILE is set and return the profile name.

    Returns:
        The AWS profile name.
    """
    profile = os.environ.get("AWS_PROFILE", "")
    if not profile:
        click.echo("Error: AWS_PROFILE environment variable is not set.", err=True)
        click.echo(
            "  Run: export AWS_PROFILE=<your-profile> && idea-app provide-role",
            err=True,
        )
        sys.exit(1)
    return profile


def _get_role_config(project_dir: Path) -> dict[str, str]:
    """Read AWS role configuration from [tool.webapp.dev] in pyproject.toml.

    Args:
        project_dir: The project root directory.

    Returns:
        Dict with "role_arn" (empty string if not configured) and "region".
    """
    pyproject_path = project_dir / "pyproject.toml"

    if not pyproject_path.exists():
        click.echo("Error: No pyproject.toml found. Are you in a project root?", err=True)
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dev_config = config.get("tool", {}).get("webapp", {}).get("dev", {})

    return {
        "role_arn": dev_config.get("aws_role_arn", ""),
        "region": dev_config.get("aws_region", DEFAULT_REGION),
    }


def _select_mode(role_arn: str, use_profile: bool) -> tuple[bool, str]:
    """Determine whether to use pass-through or role assumption mode.

    Args:
        role_arn: The role ARN from config (empty string if not configured).
        use_profile: Whether --use-profile flag was given.

    Returns:
        Tuple of (use_pass_through, reason).
    """
    if use_profile:
        return True, "--use-profile flag"
    if role_arn:
        return False, "aws_role_arn configured in pyproject.toml"
    return True, "no aws_role_arn in pyproject.toml"


def _get_current_identity(session: boto3.Session) -> dict:
    """Get current AWS identity to verify credentials are active.

    Args:
        session: A boto3 session.

    Returns:
        The caller identity response dict.
    """
    try:
        sts = session.client("sts")
        return sts.get_caller_identity()
    except NoCredentialsError as e:
        raise RuntimeError("No AWS credentials found.") from e
    except ClientError as e:
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        raise RuntimeError(f"Failed to verify AWS credentials: {error_msg}") from e


def _assume_role(session: boto3.Session, role_arn: str, duration: int) -> dict:
    """Assume the specified AWS role from current credentials.

    Args:
        session: A boto3 session.
        role_arn: The ARN of the role to assume.
        duration: Session duration in seconds.

    Returns:
        The STS assume_role response dict.
    """
    try:
        sts = session.client("sts")
        return sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="dev-container",
            DurationSeconds=duration,
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        raise RuntimeError(f"Failed to assume role ({error_code}): {error_msg}") from e


def _get_session_credentials(session: boto3.Session) -> dict:
    """Extract credentials from the current boto3 session.

    Returns credentials in the same format as STS responses for consistency
    with _assume_role output.

    Args:
        session: A boto3 session.

    Returns:
        Dict with AccessKeyId, SecretAccessKey, SessionToken, and Expiration.
    """
    try:
        credentials = session.get_credentials()
        frozen = credentials.get_frozen_credentials()

        creds = {
            "AccessKeyId": frozen.access_key,
            "SecretAccessKey": frozen.secret_key,
            "SessionToken": frozen.token,
        }

        # Try to get expiration from the credential provider
        expiration = None
        if hasattr(credentials, "_expiry_time"):
            expiration = credentials._expiry_time

        creds["Expiration"] = expiration
        return creds
    except Exception as e:
        raise RuntimeError(f"Failed to extract session credentials: {e}") from e


def _write_credentials(
    project_dir: Path,
    creds: dict,
    region: str,
    source_description: str,
) -> None:
    """Write credentials to .aws-dev/ in standard AWS format.

    Creates the .aws-dev directory if it doesn't exist. Writes both a
    credentials file and a config file.

    Args:
        project_dir: The project root directory.
        creds: Credentials dict with AccessKeyId, SecretAccessKey, SessionToken,
            and optionally Expiration.
        region: AWS region for the config file.
        source_description: Description of credential source for the comment header.
    """
    aws_dev_dir = project_dir / AWS_DEV_DIR
    aws_dev_dir.mkdir(exist_ok=True)

    expiration = creds.get("Expiration")
    if expiration:
        expiration_line = f"# Expires: {expiration}"
    else:
        expiration_line = "# Expires: unknown"

    credentials_content = (
        f"# Auto-generated by idea-app provide-role\n"
        f"# {source_description}\n"
        f"{expiration_line}\n"
        f"[default]\n"
        f"aws_access_key_id = {creds['AccessKeyId']}\n"
        f"aws_secret_access_key = {creds['SecretAccessKey']}\n"
        f"aws_session_token = {creds['SessionToken']}\n"
    )

    config_content = f"[default]\nregion = {region}\noutput = json\n"

    (aws_dev_dir / CREDENTIALS_FILE).write_text(credentials_content)
    (aws_dev_dir / CONFIG_FILE).write_text(config_content)


def _format_expiration(creds: dict) -> str:
    """Format the expiration from a credentials dict for display.

    Args:
        creds: Credentials dict with an optional Expiration key.

    Returns:
        A human-readable expiration string.
    """
    expiration = creds.get("Expiration")
    return str(expiration) if expiration else "unknown"


def run_provide_role(use_profile: bool, duration: int) -> None:
    """Provide AWS credentials to the dev container.

    Args:
        use_profile: If True, use the current AWS profile directly.
        duration: Session duration in seconds for role assumption.
    """
    project_dir = Path.cwd()

    # -- Check prerequisites --
    profile_name = _check_aws_profile()
    role_config = _get_role_config(project_dir)
    role_arn = role_config["role_arn"]
    region = role_config["region"]

    # -- Verify credentials --
    click.echo("Checking AWS credentials...")
    click.echo(f"  AWS_PROFILE: {profile_name}")

    session = boto3.Session()
    try:
        identity = _get_current_identity(session)
        current_arn = identity.get("Arn", "")
        click.echo(f"  Current identity: {current_arn}")
    except RuntimeError as e:
        click.echo()
        click.echo(f"Error: {e}", err=True)
        click.echo(
            f"  Run 'aws sso login --profile {profile_name}' first.",
            err=True,
        )
        sys.exit(1)

    # -- Determine mode --
    use_pass_through, reason = _select_mode(role_arn, use_profile)

    click.echo()
    if use_pass_through:
        click.echo(f"Mode: Pass-through ({reason})")
        click.echo(f"  Using credentials from profile: {profile_name}")
    else:
        click.echo(f"Mode: Role assumption ({reason})")
        click.echo(f"  Role: {role_arn}")
        click.echo(f"  Duration: {duration}s ({duration / 3600:.1f} hours)")

    # -- Get credentials --
    click.echo()
    if not use_pass_through:
        click.echo("Assuming role...")
        try:
            response = _assume_role(session, role_arn, duration)
            creds = response["Credentials"]
            assumed_arn = response.get("AssumedRoleUser", {}).get("Arn", "")
            source_description = f"Role: {role_arn}"
            if assumed_arn:
                click.echo(f"  Assumed identity: {assumed_arn}")
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo(
                "  Check that your profile has permission to assume the container role.",
                err=True,
            )
            sys.exit(1)
    else:
        click.echo("Extracting session credentials...")
        try:
            creds = _get_session_credentials(session)
            source_description = f"Source: AWS_PROFILE={profile_name} (pass-through)"
            click.echo(f"  Expires: {_format_expiration(creds)}")
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    # -- Write credentials --
    _write_credentials(project_dir, creds, region, source_description)

    click.echo()
    click.echo(f"Credentials written to {AWS_DEV_DIR}/")
    click.echo(f"  Expires: {_format_expiration(creds)}")
    click.echo("  No container restart needed - credentials update live.")
