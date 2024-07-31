import os
import mimetypes

import boto3
import pathlib

NEON_TESTS_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET", "neon-test-allure")
REGION = os.environ.get("AWS_REGION", "eu-central-1")
S3_ENDPOINT = f"s3-website.{REGION}.amazonaws.com"
S3_UPLOAD_URL = f"http://{NEON_TESTS_BUCKET_NAME}/{S3_ENDPOINT}/" + "{key}"

client = boto3.client("s3", region_name=REGION)


def download(source, destination, bucket=NEON_TESTS_BUCKET_NAME):
    files = list_bucket(source, bucket)
    for f in files:
        dst_file = pathlib.Path(destination) / f["Key"].split(str(source))[1][1:]
        if not dst_file.parent.exists():
            dst_file.parent.mkdir(parents=True)
        client.download_file(bucket, f["Key"], str(dst_file))


def upload(source, destination, bucket=NEON_TESTS_BUCKET_NAME):
    source = pathlib.Path(source)
    destination = pathlib.Path(destination)

    if source.is_file():
        mimetype = mimetypes.guess_type(source.name)[0]
        client.upload_file(str(source), bucket, str(destination / source.name), ExtraArgs={"ContentType": mimetype})
        return

    for f in source.glob("**/*"):
        if not f.is_file():
            continue
        mimetype = mimetypes.guess_type(f.name)[0]
        client.upload_file(
            str(f), bucket, str(destination / f.relative_to(source)), ExtraArgs={"ContentType": mimetype}
        )


def list_bucket(directory, bucket=NEON_TESTS_BUCKET_NAME):
    result = client.list_objects_v2(Bucket=bucket, Prefix=str(directory))
    return result.get("Contents", [])

