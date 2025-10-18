import boto3

s3 = boto3.client("s3", region_name="eu-west-2")

bucket_name = "test-bucket-1234som-unique-new"
s3.create_bucket(
    Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
)

print("Bucket is created")

file_name = "demo_data.csv"
s3.upload_file(file_name, bucket_name, file_name)
print("File is uploaded")

# s3.download_file(bucket_name, file_name, "download-22151.pdf")
# print("File is downloaded")

# response = s3.list_objects_v2(Bucket=bucket_name)
# if "contents" in response:
#    for obj in response["contents"]:
#        print(obj["key"])


# s3.delete_object(Bucket=bucket_name, key=file_name)
# print("File is Deleted")
