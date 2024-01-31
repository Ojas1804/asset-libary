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
4. Run the `asset_library.py` file.
5. Select 'Choose CSV File' and upload the CSV file containing the AWS access key.
6. You have two options (upload image or search image).
7. Select 'Choose Image' and upload the image you want to search for.

## Changes (v3.0.1):
- Allow users to upload multiple images of same type at once or multiple fbx files at once.

## Future work:
- Try a better Image comparison algorithm
- Improve documentation.
