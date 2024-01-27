# Asset Library

## Description
This project allows you to search similar images stored in AWS S3 buckets and upload images to S3 as well. It uses Resnet50 to vectorize images and stores the vector in a Neo4j AuraDB database. For searching, the search image is vectorized using ResNet50, and cosine similarity is used to find most similar images.

## Architecture
AWS Bucket:
- bucket
- - images
- - files

## Technologies used:
- AWS S3
- Neo4j database
- Python
- Tkinter
- PIL
- CTkinter

## How to run
1. Clone the repository `git clone https://github.com/Ojas1804/asset-libary.git`
2. Ideally create a virtual environment or conda environment and install the requirements `pip install -r requirements.txt`
3. Run the `asset_library.py` file
4. Select 'Choose CSV File' and upload the CSV file containing the AWS access key
5. You have two option (upload image or search image).
6. Select 'Choose Image' and upload the image you want to search for

## Changes (v3.0.0):
- Added option to upload directly from the app.ty
- Improved UI with CTkinter

## Future work:
- Try better Image comparison algorithm
- Better UI
- Better image comparison
