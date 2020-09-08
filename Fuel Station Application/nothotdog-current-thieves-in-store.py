# nothotdog-current-thieves-in-store

import datetime
import boto3

s3client = boto3.client(
    's3',
    'eu-west-1',
)

# --------------- Helper Functions to call Rekognition APIs ------------------
def indx_bucket(bucket):
    objs = s3client.list_objects_v2(Bucket = bucket)["Contents"]
    key_name = None
    number_thieves = 0
    for i in range(len(objs)):
        print("hi1")
        key_dt = (objs[i].get("LastModified") + datetime.timedelta(0, 36000)).replace(tzinfo = None)
        if (key_dt > (datetime.datetime.now() - datetime.timedelta(minutes = 10))):
            print("hi2")
            key_name = "https://s3-eu-west-1.amazonaws.com/nothotdog-thievesinstore/" + objs[i].get("Key")
            number_thieves = number_thieves + 1
    return([number_thieves, key_name])
    
# --------------- Main handler ------------------
def lambda_handler(event, context):
    result = indx_bucket("nothotdog-thievesinstore")
    print(result)
    return(result)
