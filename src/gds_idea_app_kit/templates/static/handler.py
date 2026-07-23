"""Generic build Lambda handler for static site generation.

This handler is injected into the user's container-image Lambda. It:
1. Runs the configured build command
2. Walks the output directory
3. Uploads all files to S3 with appropriate content types
4. Cleans up stale files from S3 (unless disabled)

Environment variables:
    CONTENT_BUCKET: S3 bucket to upload built files to
    BUILD_COMMAND: Shell command to run (e.g. 'npx eleventy')
    BUILD_OUTPUT_DIR: Directory containing build output (e.g. '_site')
    CLEAN_ON_BUILD: 'true' to delete stale files after upload (default: 'true')
    KEEP_PREFIXES: Comma-separated prefixes to never delete (e.g. 'data/,uploads/')
"""

import mimetypes
import os
import subprocess

import boto3

s3 = boto3.client("s3")

CONTENT_BUCKET = os.environ["CONTENT_BUCKET"]
BUILD_COMMAND = os.environ["BUILD_COMMAND"]
BUILD_OUTPUT_DIR = os.environ.get("BUILD_OUTPUT_DIR", "_site")
CLEAN_ON_BUILD = os.environ.get("CLEAN_ON_BUILD", "true") == "true"
KEEP_PREFIXES = [p for p in os.environ.get("KEEP_PREFIXES", "").split(",") if p]


def handler(event, context):
    """Run the build and upload output to S3."""
    print(f"Starting build: {BUILD_COMMAND}")
    print(f"Output directory: {BUILD_OUTPUT_DIR}")
    print(f"Target bucket: {CONTENT_BUCKET}")
    print(f"Clean on build: {CLEAN_ON_BUILD}")
    if KEEP_PREFIXES:
        print(f"Keep prefixes: {KEEP_PREFIXES}")

    # Run the build command
    try:
        result = subprocess.run(
            BUILD_COMMAND,
            shell=True,
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("BUILD_TIMEOUT", "600")),
        )

        print(f"Build stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Build stderr:\n{result.stderr}")

        if result.returncode != 0:
            print(f"ERROR: Build failed with exit code {result.returncode}")
            return {
                "status": "FAILED",
                "error": f"Build exited with code {result.returncode}",
                "stderr": result.stderr[:1000],
            }

    except subprocess.TimeoutExpired as e:
        print(f"ERROR: Build timed out: {e}")
        return {"status": "FAILED", "error": "Build timed out"}
    except Exception as e:
        print(f"ERROR: Failed to run build command: {e}")
        return {"status": "FAILED", "error": str(e)}

    # Upload output to S3
    uploaded_keys = _upload_directory(BUILD_OUTPUT_DIR)

    # Clean up stale files
    deleted = 0
    if CLEAN_ON_BUILD:
        deleted = _clean_stale_files(uploaded_keys)

    print(
        f"Build complete: {len(uploaded_keys)} files uploaded, "
        f"{deleted} stale files removed from s3://{CONTENT_BUCKET}"
    )
    return {
        "status": "SUCCESS",
        "files_uploaded": len(uploaded_keys),
        "files_deleted": deleted,
    }


def _upload_directory(output_dir):
    """Walk the output directory and upload all files to S3.

    Returns:
        Set of S3 keys that were uploaded.
    """
    uploaded_keys = set()

    if not os.path.isdir(output_dir):
        print(f"ERROR: Output directory '{output_dir}' does not exist")
        print(f"Current directory contents: {os.listdir('.')}")
        return uploaded_keys

    for root, _dirs, files in os.walk(output_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            # S3 key is relative to the output directory
            s3_key = os.path.relpath(local_path, output_dir)

            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"

            try:
                s3.upload_file(
                    local_path,
                    CONTENT_BUCKET,
                    s3_key,
                    ExtraArgs={"ContentType": content_type},
                )
                uploaded_keys.add(s3_key)
            except Exception as e:
                print(f"WARNING: Failed to upload {s3_key}: {e}")

    return uploaded_keys


def _clean_stale_files(uploaded_keys):
    """Delete S3 objects that weren't part of this build.

    Skips any keys matching KEEP_PREFIXES.

    Args:
        uploaded_keys: Set of S3 keys uploaded in this build.

    Returns:
        Number of stale files deleted.
    """
    deleted = 0
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=CONTENT_BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            # Skip files we just uploaded
            if key in uploaded_keys:
                continue

            # Skip files under protected prefixes
            if any(key.startswith(prefix) for prefix in KEEP_PREFIXES):
                continue

            try:
                s3.delete_object(Bucket=CONTENT_BUCKET, Key=key)
                deleted += 1
                print(f"Deleted stale file: {key}")
            except Exception as e:
                print(f"WARNING: Failed to delete {key}: {e}")

    return deleted
