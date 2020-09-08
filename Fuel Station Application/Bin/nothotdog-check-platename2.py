# nothotdog-check-platename2

import urllib.request
import json
import re
import boto3

img_name = 'car_failure.jpg'
bucket_name = 'nothotdog-pump'

rekognition = boto3.client('rekognition', 'eu-west-1')

def detect_labels(bucket, key):
    response = rekognition.detect_labels(Image = {"S3Object": {"Bucket": bucket, "Name": key}})
    return(response)

def index_face(CollectionId, bucket, key):
    response = rekognition.index_faces(CollectionId = CollectionId, Image = {'S3Object':{"Bucket": bucket,"Name": key}},
                                DetectionAttributes = ['ALL'])
    return(response)

def has_vehicle(rekog_response):
    vehicleList = ['Vehicle','Automobile','Car']
    
    # Transform rekog_response to list of objects
    resObj = []
    for label in rekog_response['Labels']:
        resObj.append(label['Name'])
    
    # Find vehicle
    for vehicle in vehicleList:
        if vehicle in resObj:
            return True
    return False

def search_faces_by_image(CollectionId, bucket, key, maxfaces):
    response = rekognition.search_faces_by_image(CollectionId = CollectionId, Image = {'S3Object':{'Bucket':bucket,'Name':key}}, 
                                                 FaceMatchThreshold = 80,
                                                 MaxFaces = maxfaces)
    return(response)

def is_person_fueling_a_theft(bucket, key):
    collection_id = "mugshot"
    
    customer_in_collection = search_faces_by_image(CollectionId = collection_id, bucket = bucket, key = key, maxfaces = 1)
    if len(customer_in_collection["FaceMatches"]) > 0:
        return(False)
    else:
        return(True)

def get_number_plate(bucket, key):
    response = rekognition.detect_text(Image = {"S3Object": {"Bucket": bucket, "Name": key}})
    
    resList = []
    for res in response['TextDetections']:
        # Get only a-z A-Z 0-9
        text_re = re.findall(r"[a-zA-Z0-9]", res['DetectedText'])
        text_result = ('').join(text_re)
        
        containsLetter = bool(re.compile(r'[a-zA-Z]+').search(text_result));
        containsDigit = bool(re.compile(r'\d+').search(text_result));
        
        # Need to be mix of number and letter
        if containsLetter and containsDigit:
            resList.append(text_result)
        
    print(resList)
        
    # If nothing found, return ''
    if len(resList) == 0:
        print('not found any text')
        return ''
    
    # Return first string with 6 in length
    for i in range(len(resList)):
        thisTxt = resList[i]
        # If length is 6, return it
        if( len(thisTxt) == 6 ):
            return thisTxt
        elif( len(thisTxt) < 6 ):
            # For text less than 6, see if we can join with the next text and get length = 6
            if(len(resList) >= i+1):
                nextTxt = resList[i+1]
                combiTxt = thisTxt + nextTxt
                if( len(combiTxt) == 6 ):
                    return combiTxt
    
    print('no text with length = 6')
    return ''

def find_car(imgname):
    # Detect if the photo is human and car or not
    resHasVehicle = has_vehicle( detect_labels(bucket_name, imgname) )
    person_is_theft = is_person_fueling_a_theft(bucket_name, imgname)
    add_person_to_fuel_collection = index_face("fueling", bucket_name, imgname)

    print('Image has vehicle:', resHasVehicle)
    
    img_url = "https://s3-eu-west-1.amazonaws.com/" + bucket_name + "/" + img_name

    # If no, alert that it is not car
    if not resHasVehicle:
        # Send Alert 'No Car'
        return json.dumps({'status': 'No car presence', "url": img_url})
    elif not person_is_theft:
        return json.dumps({'status': 'Person was a thief', "url": img_url})
    else:
        # If yes, then try to get the number plate from the car image
        numberPlate = get_number_plate(bucket_name, img_name)

        if(numberPlate):
            # - If found car plate number, then check if it is stolen or expired. Notify if it is stolen or expired
            contents = urllib.request.urlopen("http://34.241.212.158:8080/?plate_number=" + str(numberPlate)).read()
            content_json = json.loads(contents)
            return json.dumps(content_json)
        else:
            # - If not found car number plate, don't return anything
            return json.dumps({'status': 'Number plate not found', "url": img_url})

def lambda_handler(event, context):
    # Img Name = image name of what we want to detect
    return find_car(img_name);