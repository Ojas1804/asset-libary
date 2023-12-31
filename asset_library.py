import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import font as tkFont
from tkinter import scrolledtext
from PIL import Image, ImageTk
import boto3
import pandas as pd
import time
import threading


class AWSApp:
    def __init__(self, master):
        self.master = master
        self.master.title("AWS Image Similarity Search")
        helv36 = tkFont.Font(family='Helvetica', size=18, weight='bold')

        # AWS Information Entry
        tk.Label(self.master, text="Select CSV File:", font=helv36, bg="#000", fg="#fff").pack(pady=5)
        tk.Button(self.master, text="Browse Credentials", 
                  command=self.load_aws_info,font=helv36, bg="#bb86fc").pack()

        # Image Upload
        tk.Button(self.master, text="Upload Image", 
                  command=self.upload_image,font=helv36, bg="#bb86fc").pack(pady=(100, 10))

        # # Result Display
        # self.result_label = tk.Label(self.master, text="")
        # self.result_label.pack()

        # Result Display
        helv12 = tkFont.Font(family='Helvetica', size=14, weight='bold')
        self.result_text = scrolledtext.ScrolledText(self.master, bg="#121212", fg="#fff", wrap=tk.WORD, font=(helv12, 10), width  = 20, height = 10)
        self.result_text.pack(expand=True, fill="both")

        # Loader Canvas
        self.loader_canvas = tk.Canvas(self.master, width=30, height=30, bg="#121212")
        self.loader_canvas.pack()
        self.loader_animation_id = None

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


    # def upload_image(self):
    #     if self.s3_client is None or self.rekognition_client is None or self.dynamodb_client is None:
    #         tk.messagebox.showerror("Error", "AWS clients not initialized. Please load AWS info first.")
    #         return

    #     # Continue with image upload logic

    #     file_path = filedialog.askopenfilename()
    #     if file_path:
    #         image = Image.open(file_path)
    #         image.show()

    #         # Get Labels for Image
    #     labels = self.get_image_labels(file_path)

    #     # Search Similar Images
    #     similar_images = self.search_similar_images(labels)
    #     self.display_results(similar_images)
        
    #     if self.s3_client is None or self.rekognition_client is None or self.dynamodb_client is None:
    #         tk.messagebox.showerror("Error", "AWS clients not initialized. Please load AWS info first.")
    #         return
    def upload_image(self):
        if self.s3_client is None or self.rekognition_client is None or self.dynamodb_client is None:
            tk.messagebox.showerror("Error", "AWS clients not initialized. Please load AWS info first.")
            return

        file_path = filedialog.askopenfilename()
        if file_path:
            self.start_loader()
            try:
                image = Image.open(file_path)
                image.show()

                # Get Labels for Image
                labels = self.get_image_labels(file_path)

                # Search Similar Images
                similar_images = self.search_similar_images(labels)

                # Display the results on the UI
                self.display_results(similar_images)
            finally:
                self.stop_loader()
        

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

    
    # def search_similar_images(self, target_labels):
    #     # Query DynamoDB for similar images based on labels
    #     response = self.dynamodb_client.scan(
    #         TableName="image_table"  # Replace with your actual DynamoDB table name
    #     )

    #     similar_images = []
    #     for item in response['Items']:
    #         stored_labels = item.get('labels', {}).get('SS', [])

    #         # Check if there is an intersection of labels
    #         common_labels = set(target_labels) & set(stored_labels)
    #         similarity_score = len(common_labels)

    #         similar_images.append({
    #             'image_id': item.get('POID', {}).get('S', ''),
    #             'stored_labels': stored_labels,
    #             'similarity_score': similarity_score
    #         })
    #     print(similar_images)

    #     # Sort images by similarity score (descending)
    #     similar_images.sort(key=lambda x: x['similarity_score'], reverse=True)
    #     return similar_images[:10]  # Return only the top 10 most similar images
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
    

    def display_results(self, similar_images):
        self.result_text.config(state=tk.NORMAL)  # Enable text widget for editing
        self.result_text.delete(1.0, tk.END)  # Clear previous content

        if similar_images:
            for image in similar_images:
                result_text = f"Image ID: {image['image_id']}\nLabels: {', '.join(image['stored_labels'])}\n\n"
                self.result_text.insert(tk.END, result_text)
        else:
            self.result_text.insert(tk.END, "No similar images found.")

        self.result_text.config(state=tk.DISABLED)  # Disable text widget for editing

    

    def start_loader(self):
        self.loader_thread = threading.Thread(target=self.animate_loader)
        self.loader_thread.start()


    def animate_loader(self):
        self.angle = 0
        # while self.loader_thread.is_alive():
        self.loader_canvas.delete("all")
        x = 15 + 15 * (1 + 0.5 * self.angle)
        y = 15 + 15 * (1 + 0.5 * self.angle)
        self.loader_canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="white")
        # time.sleep(0.05)
        self.angle += 1
        self.loader_animation_id = self.master.after(50, self.animate_loader)  # 50 milliseconds between frames


    def stop_loader(self):
        if self.loader_animation_id:
            self.master.after_cancel(self.loader_animation_id)
            self.loader_animation_id = None
            self.loader_canvas.delete("all")
        # if self.loader_thread and self.loader_thread.is_alive():
        #     self.loader_thread.join()
        #     self.loader_thread = None
        #     self.loader_canvas.delete("all")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("500x500")
    root.config(bg='#121212')
    # root.iconbitmap("logo.ico")
    app = AWSApp(root)
    root.mainloop()
