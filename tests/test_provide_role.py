"""Tests for the provide-role command."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from gds_idea_app_kit.provide_role import (
    _check_aws_profile,
    _format_expiration,
    _get_role_config,
    _select_mode,
    _write_credentials,
)

# ---- _check_aws_profile ----


def test_check_aws_profile_returns_profile_name():
    """Returns the profile name when AWS_PROFILE is set."""
    with patch.dict("os.environ", {"AWS_PROFILE": "aws-dev"}):
        assert _check_aws_profile() == "aws-dev"


def test_check_aws_profile_exits_when_not_set():
    """Exits with error when AWS_PROFILE is not set."""
    with patch.dict("os.environ", {}, clear=True), pytest.raises(SystemExit):
        _check_aws_profile()


# ---- _get_role_config ----


def test_get_role_config_reads_role_and_region(tmp_path):
    """Reads aws_role_arn and aws_region from [tool.webapp.dev]."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.webapp.dev]\n"
        'aws_role_arn = "arn:aws:iam::123456:role/my-role"\n'
        'aws_region = "us-east-1"\n'
    )

    config = _get_role_config(tmp_path)
    assert config["role_arn"] == "arn:aws:iam::123456:role/my-role"
    assert config["region"] == "us-east-1"


def test_get_role_config_empty_role_when_not_configured(tmp_path):
    """Returns empty role_arn when [tool.webapp.dev] has no aws_role_arn."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n\n[tool.webapp]\nframework = "streamlit"\n')

    config = _get_role_config(tmp_path)
    assert config["role_arn"] == ""


def test_get_role_config_default_region(tmp_path):
    """Uses eu-west-2 as default region when aws_region is not specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.webapp.dev]\n"
        'aws_role_arn = "arn:aws:iam::123456:role/my-role"\n'
    )

    config = _get_role_config(tmp_path)
    assert config["region"] == "eu-west-2"


def test_get_role_config_exits_when_no_pyproject(tmp_path):
    """Exits with error when pyproject.toml doesn't exist."""
    with pytest.raises(SystemExit):
        _get_role_config(tmp_path)


# ---- _select_mode ----


def test_select_mode_role_assumption_when_arn_configured():
    """Uses role assumption when role_arn is configured and no --use-profile flag."""
    use_pass_through, reason = _select_mode("arn:aws:iam::123:role/r", use_profile=False)
    assert use_pass_through is False
    assert "aws_role_arn configured" in reason


def test_select_mode_pass_through_with_use_profile_flag():
    """Uses pass-through when --use-profile flag is given, even with role_arn configured."""
    use_pass_through, reason = _select_mode("arn:aws:iam::123:role/r", use_profile=True)
    assert use_pass_through is True
    assert "--use-profile" in reason


def test_select_mode_pass_through_when_no_role_arn():
    """Uses pass-through when no role_arn is configured, regardless of flag."""
    use_pass_through, reason = _select_mode("", use_profile=False)
    assert use_pass_through is True
    assert "no aws_role_arn" in reason


# ---- _write_credentials ----


def test_write_credentials_creates_both_files(tmp_path):
    """Writes both credentials and config files to .aws-dev/."""
    creds = {
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "SessionToken": "FwoGZXIvYXdzEBY",
        "Expiration": datetime(2026, 2, 16, 15, 30, 0, tzinfo=UTC),
    }

    _write_credentials(tmp_path, creds, "eu-west-2", "Role: arn:aws:iam::123:role/r")

    aws_dev = tmp_path / ".aws-dev"
    assert (aws_dev / "credentials").exists()
    assert (aws_dev / "config").exists()


def test_write_credentials_file_content(tmp_path):
    """Credentials file contains the access key, secret key, and session token."""
    creds = {
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "SessionToken": "FwoGZXIvYXdzEBY",
        "Expiration": datetime(2026, 2, 16, 15, 30, 0, tzinfo=UTC),
    }

    _write_credentials(tmp_path, creds, "eu-west-2", "Role: arn:aws:iam::123:role/r")

    content = (tmp_path / ".aws-dev" / "credentials").read_text()
    assert "AKIAIOSFODNN7EXAMPLE" in content
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in content
    assert "FwoGZXIvYXdzEBY" in content
    assert "[default]" in content
    assert "Role: arn:aws:iam::123:role/r" in content


def test_write_credentials_config_content(tmp_path):
    """Config file contains the region and output format."""
    creds = {
        "AccessKeyId": "AKIA",
        "SecretAccessKey": "secret",
        "SessionToken": "token",
    }

    _write_credentials(tmp_path, creds, "us-east-1", "test")

    content = (tmp_path / ".aws-dev" / "config").read_text()
    assert "region = us-east-1" in content
    assert "output = json" in content
    assert "[default]" in content


def test_write_credentials_creates_directory(tmp_path):
    """Creates the .aws-dev directory if it doesn't exist."""
    creds = {
        "AccessKeyId": "AKIA",
        "SecretAccessKey": "secret",
        "SessionToken": "token",
    }

    aws_dev = tmp_path / ".aws-dev"
    assert not aws_dev.exists()

    _write_credentials(tmp_path, creds, "eu-west-2", "test")

    assert aws_dev.is_dir()


def test_write_credentials_handles_no_expiration(tmp_path):
    """Writes 'unknown' when no Expiration is present in credentials."""
    creds = {
        "AccessKeyId": "AKIA",
        "SecretAccessKey": "secret",
        "SessionToken": "token",
    }

    _write_credentials(tmp_path, creds, "eu-west-2", "test")

    content = (tmp_path / ".aws-dev" / "credentials").read_text()
    assert "Expires: unknown" in content


# ---- _format_expiration ----


def test_format_expiration_with_datetime():
    """Formats a datetime expiration as a string."""
    creds = {"Expiration": datetime(2026, 2, 16, 15, 30, 0, tzinfo=UTC)}
    result = _format_expiration(creds)
    assert "2026" in result
    assert "15:30" in result


def test_format_expiration_without_expiration():
    """Returns 'unknown' when no Expiration key is present."""
    assert _format_expiration({}) == "unknown"


def test_format_expiration_with_none():
    """Returns 'unknown' when Expiration is None."""
    assert _format_expiration({"Expiration": None}) == "unknown"
