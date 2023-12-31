import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import font as tkFont
from tkinter import scrolledtext
from PIL import Image, ImageTk
import boto3
import pandas as pd
import time
import os
import tempfile
import threading


class AWSApp:
    def __init__(self, master):
        self.master = master
        self.master.title("AWS Image Similarity Search")
        helv36 = tkFont.Font(family='Helvetica', size=18, weight='bold')

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        screen_height = int(screen_height*1.5)

        # Set the app size to the screen size of the laptop
        self.master.geometry(f"{screen_width}x{screen_height}")

        # AWS Information Entry
        tk.Label(self.master, text="Select CSV File:", font=helv36, bg="#000", fg="#fff").pack(pady=5)
        tk.Button(self.master, text="Browse Credentials", 
                  command=self.load_aws_info,font=helv36, bg="#bb86fc").pack()

        # Image Upload
        tk.Button(self.master, text="Upload Image", 
                  command=self.upload_image,font=helv36, bg="#bb86fc").pack(pady=(100, 10))
        
        # Image Preview
        self.image_preview = tk.Label(self.master, text="Image Preview", bg='#121212', fg='white')
        self.image_preview.pack()


        # Result Display
        self.helv12 = tkFont.Font(family='Helvetica', size=14, weight='bold')
        self.result_frame = tk.Frame(self.master, bg='#121212')
        self.result_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center the frame
        self.result_frame.pack()

        # Initialize AWS clients
        self.s3_client = None
        self.rekognition_client = None
        self.dynamodb_client = None


    def load_aws_info(self):
        file_path = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV files", "*.csv")])
        if file_path:
            aws_info = self.read_aws_info_from_csv(file_path)
            self.initialize_aws_clients(aws_info)


    def read_aws_info_from_csv(self, file_path):
        aws_info = {}
        creds = pd.read_csv(file_path)
        aws_info['AccessKey'] = creds.iloc[0, 0]
        aws_info['SecretKey'] = creds.iloc[0, 1]
        aws_info['Region']='ap-south-1'
        print(aws_info)

        return aws_info


    def initialize_aws_clients(self, aws_info):
        try:
            self.s3_client = boto3.client('s3', aws_access_key_id=aws_info['AccessKey'],
                                          aws_secret_access_key=aws_info['SecretKey'],
                                          region_name=aws_info['Region'])
            self.rekognition_client = boto3.client('rekognition', aws_access_key_id=aws_info['AccessKey'],
                                                  aws_secret_access_key=aws_info['SecretKey'],
                                                  region_name=aws_info['Region'])
            self.dynamodb_client = boto3.client('dynamodb', aws_access_key_id=aws_info['AccessKey'],
                                                aws_secret_access_key=aws_info['SecretKey'],
                                                region_name=aws_info['Region'])
            tk.messagebox.showinfo("Success", "AWS clients initialized successfully.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to initialize AWS clients. {str(e)}")


    def upload_image(self):
        if self.s3_client is None or self.rekognition_client is None or self.dynamodb_client is None:
            tk.messagebox.showerror("Error", "AWS clients not initialized. Please load AWS info first.")
            return

        file_path = filedialog.askopenfilename()
        if file_path:
            self.uploaded_image_path = file_path

            # Display the uploaded image preview
            image = Image.open(file_path)
            image.thumbnail((300, 300))  # Adjust the size as needed
            photo = ImageTk.PhotoImage(image)

            self.image_preview.configure(image=photo)
            self.image_preview.image = photo

            # Get Labels for Image
            labels = self.get_image_labels(file_path)

            # Search Similar Images
            similar_images = self.search_similar_images(labels)

            # Display the results on the UI
            self.display_results(similar_images)
        

    def get_image_labels(self, file_path):
        with open(file_path, 'rb') as image_file:
            image_bytes = image_file.read()

        response = self.rekognition_client.detect_labels(
            Image={
                'Bytes': image_bytes
            }
        )

        # Extract labels from the response
        labels = [label['Name'] for label in response['Labels']]
        return labels

    
    def search_similar_images(self, target_labels):
        # Query DynamoDB for similar images based on labels
        response = self.dynamodb_client.scan(
            TableName="image_table"  # Replace with your actual DynamoDB table name
        )

        similar_images = []
        for item in response['Items']:
            stored_labels = item.get('labels', {}).get('SS', [])

            # Calculate false positives, false negatives, and true positives
            common_labels = set(target_labels) & set(stored_labels)
            false_positives = len(set(stored_labels) - set(target_labels))
            false_negatives = len(set(target_labels) - set(stored_labels))
            true_positives = len(common_labels)

            # Calculate precision, recall, and F1-score
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            similar_images.append({
                'image_id': item.get('POID', {}).get('S', ''),
                'stored_labels': stored_labels,
                'f1_score': f1
            })

        # Sort images by F1-score (descending)
        similar_images.sort(key=lambda x: x['f1_score'], reverse=True)

        return similar_images[:10]
    

        # self.result_text.config(state=tk.DISABLED)  # Disable text widget for editing
    def display_results(self, similar_images):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        if similar_images:
            # Display headers
            header_labels = ["POID", "SIMILARITY", "IMAGE DETAILS"]
            for col, header in enumerate(header_labels):
                tk.Label(self.result_frame, text=header, font=self.helv12).grid(row=0, column=col, sticky="nsew", padx=10, pady=4)

            # Display data
            for row, image in enumerate(similar_images, start=1):
                image_id = image['image_id']
                f1_score = image['f1_score']
                stored_labels = ', '.join(image['stored_labels'])
                # Create a button for each image
                btn = tk.Button(self.result_frame, text=image_id, command=lambda i=image_id: self.download_image(i), bg='#333', fg='white', padx=10, pady=2)
                btn.grid(row=row, column=0, sticky="nsew", padx=10, pady=2)

                tk.Label(self.result_frame, text=f"{f1_score:.4f}", bg='#121212', fg='white').grid(row=row, column=1, sticky="nsew", padx=10, pady=2)
                tk.Label(self.result_frame, text=stored_labels, bg='#121212', fg='white').grid(row=row, column=2, sticky="nsew", padx=10, pady=2)

                # Add space between rows
                self.result_frame.grid_rowconfigure(row, minsize=20)

        else:
            # tk.Label(self.result_frame, text="No similar images found.", font=("Arial", 10, "italic")).grid(row=0, column=0, columnspan=3, sticky="nsew")
            tk.Label(self.result_frame, text="No similar images found.", font=("Arial", 10, "italic"), bg='#121212', fg='white').grid(row=0, column=0, columnspan=3, sticky="nsew")

        # Configure grid weights to make it expandable
        for i in range(self.result_frame.grid_size()[1]):
            self.result_frame.grid_columnconfigure(i, weight=1)


    def download_image(self, image_id):
        if self.s3_client is None:
            tk.messagebox.showerror("Error", "AWS S3 client not initialized.")
            return

        try:
            # Replace 'your-bucket-name' with your actual S3 bucket name
            bucket_name = 'dns-assets'
            folder_path = 'images'  # Update this to the folder path where your images are stored
            object_key = f"{folder_path}/{image_id}.jpg" # Assuming images are stored with '.jpg' extension

            # Specify the local directory where you want to save the downloaded image
            local_directory = tempfile.gettempdir()

            local_path = os.path.join(local_directory, f"{image_id}.jpg")

            # Download the image from S3
            self.s3_client.download_file(bucket_name, object_key, local_path)

            # Open the downloaded image using the default viewer
            os.startfile(local_path)

        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to download image. {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("500x500")
    root.config(bg='#121212')
    # root.iconbitmap("logo.ico")
    app = AWSApp(root)
    root.mainloop()
