from __future__ import print_function
from PIL import Image
import io
from boto.s3.key import Key
import boto3
from decimal import Decimal
import json
import urllib


s3 = boto3.resource("s3","eu-west-1",)

s3client = boto3.client("s3", "eu-west-1",)

rekognition = boto3.client("rekognition", "eu-west-1",)

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

def search_faces_by_image(CollectionId, bucket, key):
    response = rekognition.search_faces_by_image(CollectionId = CollectionId, Image = {'S3Object':{'Bucket':bucket,'Name':key}}, 
                                                 FaceMatchThreshold = 80,
                                                 MaxFaces = 1)
    return(response)

def ready_img_crop(bucket, key):
    curImg = s3client.get_object(Bucket = bucket_name, Key = key)
    img = curImg["Body"].read()
    img_obj = Image.open(io.BytesIO(img))
    width, height = img_obj.size
    return(img, width, height)

def emotion_state_value(emotion_raw, emotion_dictionary):
    if (len(emotion_raw)) == 0:
        return(0)
    elif (len(emotion_raw)) == 1:
        emotion_state = emotion_dictionary.get(emotion_raw[0].get("Type"))
        return(emotion_state)
    else:
        if (emotion_raw[0].get("Confidence")/emotion_raw[1].get("Confidence")) >= 3:
            emotion_state = emotion_dictionary.get(emotion_raw[0].get("Type"))
            return(emotion_state)
        else:
            emotion_state = emotion_dictionary.get(emotion_raw[0].get("Type")) + emotion_dictionary.get(emotion_raw[1].get("Type"))
            return(emotion_state)
        
def emotion_state_string(emotion_raw, emotion_dictionary):
    if emotion_state_value(emotion_raw, emotion_dictionary) == 1:
        return("Positive")
    elif emotion_state_value(emotion_raw, emotion_dictionary) == 0:
        return("Neutral")
    elif emotion_state_value(emotion_raw, emotion_dictionary) == -1:
        return("Negative")
    
def face_in_collection(collection_id, bucket, key, emotion_dictionary):
    customer_in_collection = search_faces_by_image(CollectionId = collection_id, bucket = bucket, key = key)
    if len(customer_in_collection["FaceMatches"]) == 0:
        print("Customer NOT in collection")
        response = index_face(collection_id, bucket, key)
        age_low = response["FaceRecords"][0].get("FaceDetail").get("AgeRange").get("Low")
        age_high = response["FaceRecords"][0].get("FaceDetail").get("AgeRange").get("High")
        gender_raw = response["FaceRecords"][0].get("FaceDetail").get("Gender")
        gender = gender_raw.get("Value") if gender_raw.get("Confidence") >= 80 else "Unknown"
        emotion_raw = response["FaceRecords"][0].get("FaceDetail").get("Emotions")
        emotion = emotion_state_string(emotion_raw, emotion_dictionary)
        faceid = response["FaceRecords"][0].get("Face").get("FaceId")   
        return([age_low, age_high, gender, emotion, faceid])
    
    else:
        print("Customer IN collection")
        response = detect_faces(bucket, key)
        age_low = response["FaceDetails"][0].get("AgeRange").get("Low")
        age_high = response["FaceDetails"][0].get("AgeRange").get("High")
        gender_raw = response["FaceDetails"][0].get("Gender")
        gender = gender_raw.get("Value") if gender_raw.get("Confidence") >= 80 else "Unknown"
        emotion_raw = response["FaceDetails"][0].get("Emotions")
        emotion = emotion_state_string(emotion_raw, emotion_dictionary)
        faceid = customer_in_collection["FaceMatches"][0].get("Face").get("FaceId")
        return([age_low, age_high, gender, emotion, faceid])

def get_upper_face(response):
    x = []
    for i in range(len(response["FaceDetails"])):
        x.append(response["FaceDetails"][i].get("BoundingBox").get("Top"))
    return(max(x))
    
def crop(image_path, coords, bucket, key):
    image_obj = Image.open(io.BytesIO(image_path))
    cropped_image = image_obj.crop(coords)

    # Upload image memory to s3
    buffer = io.BytesIO()
    cropped_image.save(buffer, "JPEG")
    buffer.seek(0)

    s3client.put_object(Body = buffer,
                 Bucket = bucket,
                 Key = key)

def index_list_dict(dict_key, dict_value, dict_list):
    indx = next((index for (index, d) in enumerate(dict_list) if d[dict_key] == dict_value), None)
    return(indx)

def get_customer_feature_result(collection_id, bucket, key):
    emotion_dictionary = {"HAPPY":1, "SURPRISED":0, "CALM":0, "UNKNOWN":0, "SAD":-1, "ANGRY":-1, "DISGUSTED":-1, "CONFUSED":-1}
    status = False
    
    while status == False:
        s3bucket = s3.Bucket(bucket)
        objs = list(s3bucket.objects.filter(Prefix = key))

        if len(objs) > 0 and objs[0].key == key:
            response = detect_faces(bucket, key)
            print("First Index Done")
            img, width, height = ready_img_crop(bucket, key)

            max_top_bounding_box = get_upper_face(response)
            print("Bounding Box Done")
            s3.Object(bucket, key).delete()
            crop(img, (0, (max_top_bounding_box * height), width, height), bucket, key)

            print("Customer collection in progress")
            customer_in_collection = face_in_collection(collection_id = collection_id, bucket = bucket, key = key, emotion_dictionary = emotion_dictionary) 

            print("All Done")

            status = True

            return(customer_in_collection)

# --------------- Main handler ------------------

def lambda_handler(event, context):
    # Get the object from the event
    collection_id = "customer_faces"
    bucket = "nothotdog-customerfaces"
    key = "perthandi.jpg"

    try:
        response = get_customer_feature_result(collection_id, bucket, key)
        
        print(response)
        return(response)
    except Exception as e:
        print(e)
        print("Error processing something went wrong :(")
        raise(e)