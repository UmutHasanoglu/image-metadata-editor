import gradio as gr
from PIL import Image, ExifTags
import pandas as pd
import os
import piexif
import numpy as np
import io
import logging
import shutil
import datetime
from PIL import PngImagePlugin

logging.basicConfig(filename='metadata_update.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')  # Add formats as needed

def extract_metadata(uploaded_files, progress=gr.Progress()):
    outputs = []
    num_files = min(len(uploaded_files), 100)  # Limit to 100 images
    for idx in range(100):
        if idx < num_files:
            image_path = uploaded_files[idx]
            filename = os.path.basename(image_path)
            
            # Check if the file is in a supported format
            if not image_path.lower().endswith(SUPPORTED_FORMATS):
                outputs.extend([None, image_path, filename, "Unsupported format", "", ""])
                continue  # Skip unsupported formats
            
            try:
                img = Image.open(image_path)
                img.thumbnail((600, 600))  # Adjusted thumbnail size
                
                if img.format == 'PNG':
                    title = img.info.get('Title', '')
                    description = img.info.get('Description', '')
                    keywords = img.info.get('Keywords', '')
                else:
                    exif_data = img.getexif() if img else {}
                    exif = {}
                    for tag_id in exif_data:
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        data_value = exif_data.get(tag_id)
                        if isinstance(data_value, bytes):
                            try:
                                data_value = data_value.decode('utf-16-le').strip('\x00')
                            except UnicodeDecodeError:
                                data_value = data_value.decode(errors='replace')
                        exif[tag] = data_value

                    title = exif.get('XPTitle', '')
                    description = exif.get('ImageDescription', '')
                    keywords = exif.get('XPKeywords', '')

                # Decode if still bytes
                if isinstance(title, bytes):
                    title = title.decode('utf-16-le').strip('\x00')
                if isinstance(description, bytes):
                    description = description.decode('utf-8')
                if isinstance(keywords, bytes):
                    keywords = keywords.decode('utf-16-le').strip('\x00')

            except Exception as e:
                logger.error(f"Error processing {image_path}: {str(e)}")
                img, title, description, keywords = None, '', '', ''

            outputs.extend([img, image_path, filename, title, description, keywords])
        else:
            outputs.extend([None, '', '', '', '', ''])
        progress((idx + 1) / 100, desc=f"Processing image {idx + 1} of {num_files}")
    return outputs

def write_metadata_to_image(image_path, title, description, keywords):
    try:
        logger.info(f"Attempting to write metadata to {image_path}")
        
        # Open the image file
        with Image.open(image_path) as img:
            # Get the original format
            original_format = img.format
            
            # Prepare EXIF data for JPEG
            if original_format in ['JPEG', 'JPG']:
                exif_dict = piexif.load(img.info.get("exif", b""))
                
                # Update EXIF data
                exif_dict['0th'][piexif.ImageIFD.XPTitle] = title.encode('utf-16le')
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode('utf-8')
                exif_dict['0th'][piexif.ImageIFD.XPKeywords] = keywords.encode('utf-16le')
                
                # Convert EXIF data to bytes
                exif_bytes = piexif.dump(exif_dict)
                
                # Save with EXIF data
                img.save(image_path, exif=exif_bytes)
                logger.info(f"Metadata successfully written to {image_path}")
                
            # Prepare metadata for PNG
            elif original_format == 'PNG':
                metadata = PngImagePlugin.PngInfo()
                metadata.add_text("Title", title)
                metadata.add_text("Description", description)
                metadata.add_text("Keywords", keywords)
                
                # Save the image with metadata
                img.save(image_path, format='PNG', pnginfo=metadata)
                logger.info(f"Metadata successfully written to {image_path}")
                
            else:
                logger.error(f"Unsupported format: {original_format}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error writing metadata to {image_path}: {str(e)}")
        return False

def update_image_metadata(*args):
    success_count = 0
    error_count = 0
    image_paths = []
    
    # First, extract all image paths
    for i in range(100):
        idx = i * 6
        image_path = args[idx + 1]
        if image_path:
            image_paths.append(image_path)
    
    # Copy images to project directory
    copied_paths = copy_images_to_project_dir(image_paths)
    
    # Now update metadata for copied images
    for i, copied_path in enumerate(copied_paths):
        if copied_path:
            idx = i * 6
            title = args[idx + 3]
            description = args[idx + 4]
            keywords = args[idx + 5]
            if write_metadata_to_image(copied_path, title, description, keywords):
                success_count += 1
            else:
                error_count += 1

    return f"Images copied and metadata updated. Successful updates: {success_count}, Failed updates: {error_count}. Check the 'edited_images' folder for results."

def copy_images_to_project_dir(image_paths):
    copied_paths = []
    for path in image_paths:
        if path and os.path.isfile(path):
            filename = os.path.basename(path)
            new_path = os.path.join("edited_images", filename)
            os.makedirs("edited_images", exist_ok=True)
            shutil.copy2(path, new_path)
            copied_paths.append(new_path)
        else:
            copied_paths.append(None)
    return copied_paths

def save_csv(*args):
    data = []
    for i in range(100):
        idx = i * 6
        img = args[idx]  # Not used, but kept for consistency
        image_path = args[idx + 1]
        filename = args[idx + 2]
        title = args[idx + 3]
        description = args[idx + 4]
        keywords = args[idx + 5]
        if filename:
            data.append({
                'Filename': filename,
                'Title': title,
                'Description': description,
                'Keywords': keywords,
            })
    df = pd.DataFrame(data)
    try:
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f'edited_metadata_{timestamp}.csv'
        df.to_csv(csv_filename, index=False)
        return f"Data saved successfully to '{csv_filename}'!"
    except Exception as e:
        return f"Error saving data: {e}"

# Functions to update character and keyword counts
def update_title_info(text):
    return f"{len(text)} characters"

def update_description_info(text):
    return f"{len(text)} characters"

def update_keywords_info(text):
    keywords = [k.strip() for k in text.split(',') if k.strip()]
    return f"{len(keywords)} keywords"

with gr.Blocks(css="""
    .counter {
        font-size: 12px;
        color: #555;
        margin-top: -8px;
        margin-bottom: 8px;
    }
    .metadata-section {
        border: 1px solid #ccc;
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 5px;
    }
    .thumbnail {
        flex-shrink: 0;
    }
    .metadata-fields {
        flex-grow: 1;
        margin-left: 10px;
    }
    .container {
        max-width: 1200px;
        margin: auto;
    }
""") as demo:
    gr.Markdown("## Image Metadata Editor")
    with gr.Column():
        file_input = gr.File(label="Select Images", file_count="multiple", type="filepath")
        extract_button = gr.Button("Extract Metadata")
    
    # Lists to hold component references
    image_components = []
    filename_components = []
    title_components = []
    title_info_components = []
    description_components = []
    description_info_components = []
    keywords_components = []
    keywords_info_components = []

    for i in range(100):
        with gr.Row():
            # Thumbnail Image
            with gr.Column(scale=1):
                image = gr.Image(label="Thumbnail", interactive=False, width=600, height=600)
                image_components.append(image)
            # Metadata Fields
            with gr.Column(scale=3):
                filename = gr.Textbox(label="Filename", interactive=False, placeholder="Filename")
                filename_components.append(filename)
                
                title = gr.Textbox(label="Title", lines=1, placeholder="Enter title")
                title_components.append(title)
                title_info = gr.Text(label="", value="0 characters", interactive=False, elem_classes="counter")
                title_info_components.append(title_info)
                
                description = gr.Textbox(label="Description", lines=2, placeholder="Enter description")
                description_components.append(description)
                description_info = gr.Text(label="", value="0 characters", interactive=False, elem_classes="counter")
                description_info_components.append(description_info)
                
                keywords = gr.Textbox(label="Keywords", lines=1, placeholder="Enter keywords separated by commas")
                keywords_components.append(keywords)
                keywords_info = gr.Text(label="", value="0 keywords", interactive=False, elem_classes="counter")
                keywords_info_components.append(keywords_info)
                
                # Link change events to update counters
                title.change(fn=update_title_info, inputs=title, outputs=title_info)
                description.change(fn=update_description_info, inputs=description, outputs=description_info)
                keywords.change(fn=update_keywords_info, inputs=keywords, outputs=keywords_info)

    # Save Buttons and Output
    with gr.Row():
        save_metadata_button = gr.Button("Save Metadata to Images")
        save_csv_button = gr.Button("Save CSV")
        save_output = gr.Textbox(label="Save Status", interactive=False)

    # Collect all output components for extraction and saving
    all_outputs = []
    for i in range(100):
        all_outputs.extend([
            image_components[i],
            gr.Textbox(visible=False),  # Hidden textbox to store full image path
            filename_components[i],
            title_components[i],
            description_components[i],
            keywords_components[i]
        ])

    # Define the interactions
    extract_button.click(
        fn=extract_metadata,
        inputs=file_input,
        outputs=all_outputs
    )

    save_metadata_button.click(
        fn=update_image_metadata,
        inputs=all_outputs,
        outputs=save_output
    )

    save_csv_button.click(
        fn=save_csv,
        inputs=all_outputs,
        outputs=save_output
    )

demo.launch()
