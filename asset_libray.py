import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk
import boto3
import tempfile
import os
from tkinter import font as tkFont
from tkinter import scrolledtext
import customtkinter as ctk
import pandas as pd
import torch
import torchvision.transforms as transforms
import time
import traceback
import torchvision.models as models
from PIL import Image
from neo4j import GraphDatabase
from scipy import spatial
import numpy as np
from botocore.exceptions import NoCredentialsError

# enter your Neo4j credentials here
uri = ""
username = ""
password = ""

class Neo4jDatabase:
    def __init__(self):
        self._driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self._driver.close()

    def create_image_node(self, embeddings, name, image_type):
        with self._driver.session() as session:
            session.execute_write(self._create_image_node, embeddings, name, image_type)

    @staticmethod
    def _create_image_node(tx, embeddings, name, type):
        query = (
            "CREATE (img:Image {embeddings: $embeddings,name: $name,type: $type})"
        )
        tx.run(query, embeddings=embeddings,name = name, type = type)



class AWSApp:
    def __init__(self, master):
        self.master = master
        self.master.title("AWS Image App")
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        self.master.geometry(f"{screen_width}x{screen_height}")

        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=(10, 8), font=('Arial', 14))

        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Initialize AWS clients
        self.s3_client = None
        self.rekognition_client = None
        self.dynamodb_client = None

        # Track the uploaded image path
        self.uploaded_image_path = None

        self.upload_frame = UploadFrame(self.notebook)
        self.notebook.add(self.upload_frame.frame, text="Upload Images")

        self.search_frame = SearchFrame(self.notebook)
        self.notebook.add(self.search_frame.frame, text="Find Similar Images")

        # Set the initial tab
        self.notebook.select(self.upload_frame.frame)


        
class UploadFrame:
    def __init__(self, notebook):
        self.notebook = notebook
        self.s3_client = None
        self.dynamodb_client = None
        # Initialize AWS clients

        self.frame = tk.Frame(self.notebook, bg='#121212')
        self.frame.pack(fill=tk.BOTH, expand=True)

        helv36 = tkFont.Font(family='Courier', size=18, weight='bold')

        button_font = ctk.CTkFont(family='Courier', size=24, weight='bold')

        # AWS Information Entry
        tk.Label(self.frame, text="Select CSV File:", font=helv36, bg="#000", 
                 fg="#fff").pack(pady=10)
        ctk.CTkButton(self.frame, text="Browse Access Key", command=self.load_aws_info,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack()

        self.image_path_label = tk.Label(self.frame, text="Image Path:", bg='#121212', fg='white')
        self.image_path_label.pack(pady=(100, 0))

        # Image Upload
        ctk.CTkButton(self.frame, text="Upload Image", command=self.browse_image,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack(pady=(0, 10))

        self.image_type_label = tk.Label(self.frame, text="Image Type:", bg='#121212', fg='white')
        self.image_type_label.pack()

        self.image_type_entry = tk.Entry(self.frame, bg='#484848', fg='white')
        self.image_type_entry.pack(pady=10)

        # Image Upload
        ctk.CTkButton(self.frame, text="Upload FBX", command=self.browse_fbx,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack(pady=(0, 10))

        ctk.CTkButton(self.frame, text="Submit", command=self.submit_image,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack(pady=30)
    

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
            tk.messagebox.showinfo("Success", "AWS clients initialized successfully.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to initialize AWS clients. {str(e)}")


    def browse_image(self):
        file_path = filedialog.askopenfilename()
        self.image_path_label.config(text="Image Path: " + file_path)
        self.uploaded_image_path = file_path


    def browse_fbx(self):
        file_path = filedialog.askopenfilename()
        self.image_path_label.config(text="FBX Path: " + file_path)
        self.uploaded_fbx_path = file_path


    def submit_image(self):
        if not self.uploaded_image_path:
            messagebox.showerror("Error", "Please choose an image first.")
            return

        image_type = self.image_type_entry.get()
        if not image_type:
            messagebox.showerror("Error", "Please enter an image type.")
            return

        try:
            # Upload image to S3
            image_name = os.path.basename(self.uploaded_image_path)
            s3_key_image = f'images/{image_name}'
            self.s3_client.upload_file(self.uploaded_image_path, 'dns-assets', s3_key_image)

            # Vectorize the image using InceptionV3 model
            image_vector = self.vectorize_image(self.uploaded_image_path)

            # Upload image information to Neo4j
            self.upload_to_neo4j(image_name, image_vector, image_type)

            if self.uploaded_fbx_path:
                s3_key_fbx = f'fbx/{os.path.basename(self.uploaded_fbx_path)}'
                self.s3_client.upload_file(self.uploaded_fbx_path, 'dns-assets', s3_key_fbx)

            messagebox.showinfo("Success", "Files uploaded successfully!")

        except Exception as e:
            messagebox.showerror("Error", str(e))


    def vectorize_image(self, image_path):

        # return image_vector.tolist()
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        model = torch.nn.Sequential(*list(model.children())[:-1]) 
        img = Image.open(image_path).convert('RGB')
        img = preprocess(img)
        img = img.unsqueeze(0)  # Add batch dimension
        with torch.no_grad():
            embeddings = model(img)
        return embeddings.squeeze().numpy()
    

    def upload_to_neo4j(self, image_name, embedding, image_type):
        neo4j_db = Neo4jDatabase()
        neo4j_db.create_image_node(embedding, image_name, image_type)



class SearchFrame:

    def __init__(self, notebook):
        # self.master = master
        self.notebook = notebook
        self.frame = tk.Frame(self.notebook, bg='#121212')
        self.frame.pack(fill=tk.BOTH, expand=True)
        helv36 = tkFont.Font(family='Courier', size=18, weight='bold')

        button_font = ctk.CTkFont(family='Courier', size=24, weight='bold')

        # AWS Information Entry
        tk.Label(self.frame, text="Select CSV File:", font=helv36, bg="#000", 
                 fg="#fff").pack(pady=10)
        ctk.CTkButton(self.frame, text="Browse Access Key", command=self.load_aws_info,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack()
        
        self.image_type_label = tk.Label(self.frame, text="Image Type:", bg='#121212', fg='white')
        self.image_type_label.pack(pady=(100, 0))

        self.image_type_entry = tk.Entry(self.frame, bg='#484848', fg='white')
        self.image_type_entry.pack(pady=(0, 0))

        # Image Upload
        ctk.CTkButton(self.frame, text="Search Image", command=self.search_image,
                      font=button_font, corner_radius=10, fg_color='#bb86fc', text_color='#000',
                      hover_color='#a435f0').pack(pady=(10, 10))

        # Result Display
        self.helv12 = tkFont.Font(family='Courier', size=12)
        self.result_frame = tk.Frame(self.frame, bg='#121212')
        self.result_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Center the frame
        self.result_frame.pack()

        # Result Display
        self.result_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, bg='#121212', fg='white', insertbackground='white', selectbackground='#444', selectforeground='white', font=self.helv12)
        self.result_text.pack()

        # Initialize AWS clients
        self.s3_client = None

        # Configure ttk.Style to use curved edges for buttons
        style = ttk.Style()

        # Apply styling to buttons
        style.configure('TButton', borderwidth=0, focuscolor='#121212', lightcolor='#121212', darkcolor='#121212', relief='flat', background='#444', foreground='white', padding=10, font=('Arial', 10))
        style.map('TButton', background=[('active', '#555')])


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
            tk.messagebox.showinfo("Success", "AWS clients initialized successfully.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to initialize AWS clients. {str(e)}")


    def search_image(self):
        if self.s3_client is None:
            tk.messagebox.showerror("Error", "AWS client not initialized. Please load AWS info first.")
            return
        image_type = self.image_type_entry.get()
        file_path = filedialog.askopenfilename()
        if file_path:
            self.uploaded_image_path = file_path

            # Display the uploaded image preview
            image = Image.open(file_path)
            image.thumbnail((300, 300))  # Adjust the size as needed
            photo = ImageTk.PhotoImage(image)

            # Search Similar Images
            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

            model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
            model = torch.nn.Sequential(*list(model.children())[:-1])
            img = Image.open(file_path).convert('RGB')
            img = preprocess(img)
            img = img.unsqueeze(0)  # Add batch dimension
            with torch.no_grad():
                embeddings = model(img)
            embeddings = embeddings.squeeze().numpy()
            similar_images = self.search_similar_images(embeddings, image_type)

            # Display the results on the UI
            i = 0
            similar_images_list = []
            for key in similar_images.keys():
                if i == 10:
                    break
                similar_images_list.append(key)
            self.display_results(similar_images_list)
        

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

    
    def search_similar_images(self, embeddings, image_type):
        
        uri = ""
        username = ""
        password = ""

        driver_con = GraphDatabase.driver(uri, auth=(username, password))
        query = (
        """
        MATCH (n:Image)
        where n.type=$image_type
        RETURN n.embeddings as embedding, n.name as path;
        """
        )
        with driver_con.session() as session:
            images = {}
            result = session.run(query, image_type=image_type)
            print(result)
            for record in result:
                images[record['path']] = record['embedding']
            similarity = {}
            for key in images.keys():
                similarity[key] = 1 - spatial.distance.cosine(embeddings, images[key])
            similarity = dict(sorted(similarity.items(), key=lambda item: item[1]))
        return similarity
    

    def create_button(self, image_id):
        download_button = ctk.CTkButton(self.result_text, text=f"Download Image {image_id}", 
                                    command=lambda i=image_id: self.download_image(i), 
                                    font=('Helvetica', 12), fg_color='#ac7ed7', 
                                    text_color='black', hover_color='#a435f0')

        return download_button
    

        # self.result_text.config(state=tk.DISABLED)  # Disable text widget for editing
    def display_results(self, similar_images):
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        if similar_images:
            # Display data
            for image in similar_images:
                # image_id = image['image_id']
                image_id = image
                result_text = f"POID: {image_id}\n"
                self.result_text.insert(tk.END, result_text)

                # Add a button for each row (image ID)
                download_button = self.create_button(image_id)
                self.result_text.window_create(tk.END, window=download_button)
                self.result_text.insert(tk.END, '\n\n\n')

        else:
            self.result_text.insert(tk.END, "No similar images found.")

        # Configure grid weights to make it expandable
        for i in range(self.result_frame.grid_size()[1]):
            self.result_frame.grid_columnconfigure(i, weight=1)
        self.result_text.config(state=tk.DISABLED)


    def download_image(self, image_id):
        if self.s3_client is None:
            # tk.messagebox.showerror("Error", "AWS S3 client not initialized.")
            tk.messagebox.showinfo("Download Image", f"Downloading image with ID: {image_id}")
            return

        try:
            # Replace 'your-bucket-name' with your actual S3 bucket name
            bucket_name = 'dns-assets'
            folder_path = 'images'  # Update this to the folder path where your images are stored
            object_key = f"{folder_path}/{image_id}" # Assuming images are stored with '.jpg' extension
            print(object_key)
            # Specify the local directory where you want to save the downloaded image
            local_directory = tempfile.gettempdir()
            print(local_directory)

            local_path = os.path.join(local_directory, f"{image_id}")

            # Download the image from S3
            i = 0
            sleep = 2
            retries=3
            while(i <= retries):
                try:
                    # self.s3_client.download_file(bucket,s3_path,local_path)
                    self.s3_client.download_file(bucket_name, object_key, local_path)
                    break
                except Exception as e:            
                    print("404 file not found !!!")
                    i = i+1
                    if i>retries:
                        raise Exception(traceback.format_exc())
                    time.sleep(sleep)
                    sleep = sleep*2
                    print("retry: "+str(i))
            # self.s3_client.download_file(bucket_name, object_key, local_path)

            # Open the downloaded image using the default viewer
            os.startfile(local_path)

        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to download image. {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AWSApp(root)
    root.configure(bg='#121212')
    root.mainloop()

