#import json
#import requests

import boto3
import uuid
import os
import io

from PIL import Image
from PIL.ExifTags import TAGS as ExifTags

landscape = [
    (1024, 768),
    (800, 600),
    (640, 480),
    (320, 240),
    (240, 180)
]

portrait = [
    (768, 1024),
    (600, 800),
    (480, 640),
    (240, 320),
    (180, 240)
]

def load_exif(im):
    tags = im._getexif()
    return dict([(ExifTags[k], tags[k]) for k in ExifTags if k in tags])

def download_image (s3, bucket, key):
    buffer = io.BytesIO()
    s3.download_fileobj(bucket, key, buffer)
    buffer.seek(0)
    return Image.open(buffer)

def upload_sized_image(s3, bucket, key, image, size):
    buffer = io.BytesIO()
    imc = image.copy()
    imc.thumbnail(size, Image.ANTIALIAS)
    imc.save(buffer, "JPEG")
    s3.upload_fileobj(buffer, bucket, f'{key}/{size[0]}_{size[1]}.jpg')

def new_sizes(im):
    (width,height) = im.size
    sizes = [(width,height)]
    if width>height:
        sizes.extend(landscape)
    else:
        sizes.extend(portrait)
    return sizes

def process_record(s3, table, record):
    im = download_image(s3, record['s3']['bucket']['name'], record['s3']['object']['key'])
    exif = load_exif(im)
    sizes = new_sizes(im)
    name = str(uuid.uuid4())

    table.put_item(
        Item={
            'event_id': name,
            'image_date': exif['DateTimeOriginal'],
            'exif':exif
        }
    )
    for size in sizes:
        upload_sized_image(s3, os.environ['DestBucket'], name, im, size)
    
def lambda_handler(event, context):
    '''
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('bucket_updates')
    return table.put_item(Item={
        'event_id': context.aws_request_id,
        'dest_bucket': os.environ['DestBucket'],
        'dump_data': event
    })
    '''

    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('bucket_updates')
    for record in event['Records']:
        process_record(s3, table, record)
