# Asset Library

## Description
This project allows you to search similar images stored in AWS S3 buckets and upload images to S3 as well. It uses Resnet50 to vectorize images and stores the vector in a Neo4j AuraDB database. For searching, the search image is vectorized using ResNet50, and cosine similarity is used to find the most similar images.

## Working
![Flowchart](https://github.com/Ojas1804/asset-libary/blob/main/asset-library.jpg)

## Architecture
AWS Bucket:
- bucket
- - images
- - files

## Technologies used:
- AWS S3
- Neo4j (AuraDB)
- Python
- Tkinter
- PIL
- CTkinter

## How to run
1. Clone the repository `git clone https://github.com/Ojas1804/asset-libary.git`
2. Ideally, create a virtual environment or conda environment and install the requirements `pip install -r requirements.txt`.
3. Create an instance in AuraDB in Neo4j cloud and add the required details in the code.
4. Create a bucket in S3 and two folders inside the bucket called images and FBX.
5. Run the `asset_library.py` file.
6. Select 'Choose CSV File' and upload the CSV file containing the AWS access key.
7. You have two options (upload image or search image).
8. Select 'Choose Image' and upload the image you want to search for.
**Before using the app, you must setup AWS credentials on AWS CLI. Install AWS CLI on your system and then in youe command prompt type `aws configure` and input the details.**

## Changes (v3.0.1):
- Allow users to upload multiple images of same type at once or multiple fbx files at once.

## Future work:
- Try a better Image comparison algorithm
- Improve documentation.
