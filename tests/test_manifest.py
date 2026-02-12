"""Tests for manifest module."""

import hashlib

import pytest

from gds_idea_app_kit.manifest import (
    build_manifest,
    get_tracked_files,
    hash_file,
    read_manifest,
    write_manifest,
)

# ---- fixtures ----


@pytest.fixture()
def sample_file(tmp_path):
    """A simple text file for hashing tests."""
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    return f


@pytest.fixture()
def tracked_project(project_dir):
    """A project directory with all tool-owned files present."""
    (project_dir / "app_src").mkdir()
    (project_dir / "app_src" / "Dockerfile").write_text("FROM python:3.13-slim")
    (project_dir / ".devcontainer").mkdir()
    (project_dir / ".devcontainer" / "devcontainer.json").write_text("{}")
    (project_dir / ".devcontainer" / "docker-compose.yml").write_text("services:")
    (project_dir / "dev_mocks").mkdir()
    (project_dir / "dev_mocks" / "dev_mock_authoriser.json").write_text("{}")
    (project_dir / "dev_mocks" / "dev_mock_user.json").write_text("{}")
    return project_dir


# ---- hash_file ----


def test_hash_file_returns_sha256_prefix(sample_file):
    result = hash_file(sample_file)
    expected = f"sha256:{hashlib.sha256(b'hello world').hexdigest()}"
    assert result == expected


def test_hash_file_different_content_gives_different_hash(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("content a")
    b = tmp_path / "b.txt"
    b.write_text("content b")
    assert hash_file(a) != hash_file(b)


def test_hash_file_same_content_gives_same_hash(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("same")
    b = tmp_path / "b.txt"
    b.write_text("same")
    assert hash_file(a) == hash_file(b)


def test_hash_file_empty(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("")
    expected = f"sha256:{hashlib.sha256(b'').hexdigest()}"
    assert hash_file(f) == expected


def test_hash_file_binary(tmp_path):
    f = tmp_path / "bin.dat"
    data = b"\x00\x01\x02\xff"
    f.write_bytes(data)
    expected = f"sha256:{hashlib.sha256(data).hexdigest()}"
    assert hash_file(f) == expected


# ---- get_tracked_files ----


@pytest.mark.parametrize("framework", ["streamlit", "dash", "fastapi"])
def test_tracked_files_include_common_destinations(framework):
    tracked = get_tracked_files(framework)
    destinations = set(tracked.values())
    assert ".devcontainer/devcontainer.json" in destinations
    assert ".devcontainer/docker-compose.yml" in destinations
    assert "dev_mocks/dev_mock_authoriser.json" in destinations
    assert "dev_mocks/dev_mock_user.json" in destinations
    assert "app_src/Dockerfile" in destinations


@pytest.mark.parametrize("framework", ["streamlit", "dash", "fastapi"])
def test_tracked_files_dockerfile_source_matches_framework(framework):
    tracked = get_tracked_files(framework)
    assert f"{framework}/Dockerfile" in tracked


def test_tracked_files_differ_across_frameworks():
    streamlit = get_tracked_files("streamlit")
    fastapi = get_tracked_files("fastapi")
    assert "streamlit/Dockerfile" in streamlit
    assert "streamlit/Dockerfile" not in fastapi
    assert "fastapi/Dockerfile" in fastapi


# ---- read_manifest ----


def test_read_manifest_missing_pyproject(tmp_path):
    assert read_manifest(tmp_path) == {}


def test_read_manifest_no_manifest_section(project_dir):
    assert read_manifest(project_dir) == {}


def test_read_manifest_existing(project_with_manifest):
    result = read_manifest(project_with_manifest)
    assert result["framework"] == "streamlit"
    assert result["app_name"] == "test-app"
    assert result["tool_version"] == "0.1.0"
    assert result["files"]["app_src/Dockerfile"] == "sha256:abc123"
    assert result["files"][".devcontainer/devcontainer.json"] == "sha256:def456"


# ---- write_manifest ----


@pytest.fixture()
def sample_manifest():
    return {
        "framework": "fastapi",
        "app_name": "my-api",
        "tool_version": "0.2.0",
        "files": {"app_src/Dockerfile": "sha256:aaa111"},
    }


def test_write_manifest_creates_section(project_dir, sample_manifest):
    write_manifest(project_dir, sample_manifest)
    result = read_manifest(project_dir)
    assert result["framework"] == "fastapi"
    assert result["app_name"] == "my-api"
    assert result["files"]["app_src/Dockerfile"] == "sha256:aaa111"


def test_write_manifest_preserves_existing_content(project_dir, sample_manifest):
    write_manifest(project_dir, sample_manifest)
    content = (project_dir / "pyproject.toml").read_text()
    assert 'name = "test-app"' in content
    assert 'version = "0.1.0"' in content


def test_write_manifest_overwrites_previous(project_with_manifest, sample_manifest):
    write_manifest(project_with_manifest, sample_manifest)
    result = read_manifest(project_with_manifest)
    assert result["framework"] == "fastapi"
    assert result["app_name"] == "my-api"
    assert ".devcontainer/devcontainer.json" not in result["files"]


# ---- build_manifest ----


def test_build_manifest_hashes_all_tracked_files(tracked_project):
    result = build_manifest(
        framework="streamlit",
        app_name="test-app",
        tool_version="0.1.0",
        project_dir=tracked_project,
    )
    assert result["framework"] == "streamlit"
    assert result["app_name"] == "test-app"
    assert result["tool_version"] == "0.1.0"
    assert len(result["files"]) == 5
    for file_hash in result["files"].values():
        assert file_hash.startswith("sha256:")


def test_build_manifest_skips_missing_files(project_dir):
    (project_dir / "app_src").mkdir()
    (project_dir / "app_src" / "Dockerfile").write_text("FROM python:3.13-slim")

    result = build_manifest(
        framework="streamlit",
        app_name="test-app",
        tool_version="0.1.0",
        project_dir=project_dir,
    )
    assert "app_src/Dockerfile" in result["files"]
    assert ".devcontainer/devcontainer.json" not in result["files"]


def test_build_manifest_hash_matches_content(project_dir):
    content = "FROM python:3.13-slim AS base"
    (project_dir / "app_src").mkdir()
    (project_dir / "app_src" / "Dockerfile").write_text(content)

    result = build_manifest(
        framework="streamlit",
        app_name="test-app",
        tool_version="0.1.0",
        project_dir=project_dir,
    )
    expected = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
    assert result["files"]["app_src/Dockerfile"] == expected


# ---- round-trip ----


def test_build_write_read_roundtrip(tracked_project):
    """build_manifest -> write_manifest -> read_manifest gives consistent data."""
    manifest = build_manifest(
        framework="streamlit",
        app_name="roundtrip-app",
        tool_version="0.1.0",
        project_dir=tracked_project,
    )
    write_manifest(tracked_project, manifest)
    result = read_manifest(tracked_project)

    assert result["framework"] == manifest["framework"]
    assert result["app_name"] == manifest["app_name"]
    assert result["tool_version"] == manifest["tool_version"]
    assert dict(result["files"]) == manifest["files"]
