# checkout 

import json
import pymysql
import os
import datetime

conn = pymysql.connect(host='nothotdog.cd2qzps9nyc6.eu-west-1.rds.amazonaws.com', port=3306, user='nothotdog', passwd='nothotdog', db='nothotdog',connect_timeout=3)

def lambda_handler(event, context):
    if(event['queryStringParameters']):
        checkout_data = json.loads(event['queryStringParameters']['checkout'])
        face_id = checkout_data['face_id']
        age_low = checkout_data['age_low']
        age_high = checkout_data['age_high']
        emotion = checkout_data['emotion']
        gender = checkout_data['gender']
        products = checkout_data['products']
        
        now = datetime.datetime.now()
        nowdate = now.strftime("%d/%m/%Y")
        nowtime = now.strftime("%H")
        
        for product in products:
            product_id = product['product_id']
            product_quantity = product['quantity']
            product_cost = product['total_price']
            
            # Store it into RDS
            with conn.cursor() as cur:
                select_statement = "INSERT INTO transaction VALUES ('" + str(nowdate) + "'," + str(nowtime) + ",'" + face_id + "'," + str(product_id) + "," + str(product_quantity) + "," + str(product_cost) + ");"
                cur.execute(select_statement)
                result = cur.fetchall()
            conn.commit()
        
        # Return if it successfully checkout
        
        # TODO implement
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": { 'Access-Control-Allow-Origin': '*' },
            "body": json.dumps({ 'result':select_statement })
        }
    else:
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": { 'Access-Control-Allow-Origin': '*' },
            "body": json.dumps({ 'result': 'no_checkout_data' })
        }