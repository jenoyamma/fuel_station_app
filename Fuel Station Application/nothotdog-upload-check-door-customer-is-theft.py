# nothotdog-upload-check-door-customer-is-theft

from __future__ import print_function

import boto3
from decimal import Decimal
import json
import urllib

print('Loading function')

rekognition = boto3.client('rekognition')

# --------------- Helper Functions to call Rekognition APIs ------------------
def detect_labels(bucket, key):
    response = rekognition.detect_labels(Image = {"S3Object": {"Bucket": bucket, "Name": key}})
    return(response)

def detect_faces(bucket, key):
    response = rekognition.detect_faces(Image = {"S3Object": {"Bucket": bucket, "Name": key}}, Attributes = ["ALL"])
    return(response)

def index_face(CollectionId, bucket, key):
    response = rekognition.index_faces(CollectionId = CollectionId, Image = {'S3Object':{"Bucket": bucket,"Name": key}},
                                DetectionAttributes = ['ALL'])
    return(response)

def search_faces_by_image(CollectionId, bucket, key, maxfaces):
    response = rekognition.search_faces_by_image(CollectionId = CollectionId, Image = {'S3Object':{'Bucket':bucket,'Name':key}}, 
                                                 FaceMatchThreshold = 80,
                                                 MaxFaces = maxfaces)
    return(response)

def get_img_dimensions(bucket, key):
    curImg = s3client.get_object(Bucket = bucket, Key = key)
    img = curImg["Body"].read()
    img_obj = Image.open(io.BytesIO(img))
    width, height = img_obj.size
    return(img, img_obj, width, height)

def draw_bounding_box(collectionid, bucket, bucket2, key):
    customer_is_mug = search_faces_by_image(collectionid, bucket, key, 10)
    
    if len(customer_is_mug["FaceMatches"]) > 0:

        img, img_obj, width_m, height_m = get_img_dimensions(bucket, key)

        for i in range(len(customer_is_mug["FaceMatches"])):
            matched_faces = customer_is_mug["FaceMatches"][i].get("Face").get("BoundingBox")
            left = matched_faces.get("Left")
            top = matched_faces.get("Top")
            width = matched_faces.get("Width")    
            height = matched_faces.get("Height")

            x1 = left * width_m
            x2 = x1 + (width * width_m)
            y1 = top * height_m
            y2 = y1 + (height * height_m)

            draw = ImageDraw.Draw(img_obj)
            draw.rectangle(((x1, y1), (x2, y2)), outline = "Red")

        buffer = io.BytesIO()
        img_obj.save(buffer, "JPEG")
        buffer.seek(0)

        s3client.put_object(Body = buffer, Bucket = bucket2, Key = key)

    s3.Object(bucket, key).delete()
        
    print("Finish")


# --------------- Main handler ------------------

def lambda_handler(event, context):
    # Get the object from the event
    collectionid = "mugshot"
    
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.quote_plus(event["Records"][0]["s3"]["object"]["key"].encode("utf8"))
    
    bucket2 = "nothotdog-thievesinstore"
    
    try:
        # Check if customer is a theft and draw bounding box
        response = draw_bounding_box(collectionid, bucket, bucket2, key)

        print("Done")

        return response
    except Exception as e:
        print(e)
        print("Error processing object {} from bucket {}. ".format(key, bucket) +
              "Make sure your object and bucket exist and your bucket is in the same region as this function.")
        raise e
