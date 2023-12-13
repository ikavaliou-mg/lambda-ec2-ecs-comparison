import boto3
import uuid
import os
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()
s3 = boto3.resource("s3")
dynamo_db = boto3.resource("dynamodb")


@app.get("/")
def process_request():
    bucket_name = os.environ["S3_BUCKET_NAME"]
    ddb_table = os.environ["DYNAMODB_TABLE"]

    guid = str(uuid.uuid4())
    encoded_string = guid.encode("utf-8")
    file_name = f"{guid}.txt"
    s3.Bucket(bucket_name).put_object(Key=file_name, Body=encoded_string)

    table = dynamo_db.Table(ddb_table)
    table.put_item(Item={"id": guid})

    return {"id": guid}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    os.environ["S3_BUCKET_NAME"] = "test_s3"
    os.environ["DYNAMODB_TABLE"] = "test_table"
    process_request()
