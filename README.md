# Asset Library

## Description
This project allows you to search similar images stored in AWS S3 buckets. It uses AWS Rekognition to detect objects in images and stores the data in a DynamoDB table. The data is then used to search for similar images.

## Architecture
AWS Bucket:
--- bucket
------ images
------ files

## Technologies used:
- AWS S3
- AWS Rekognition
- AWS DynamoDB
- AWS Lambda
- Python
- Tkinter

## How to run
1. Clone the repository `git clone https://github.com/Ojas1804/asset-libary.git`
2. Install the requirements
3. Run the `asset_library.py` file
4. Select 'Choose CSV File' and upload the CSV file containing AWS access key
5. Select 'Choose Image' and upload the image you want to search for

## Changes (v1.0.1):
- Added download button for downloading the image directly from the app.
- Improved UI
