import gradio as gr
from PIL import Image, ExifTags
import pandas as pd
import os
import datetime

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
                outputs.extend([None, filename, "Unsupported format", "", ""])
                continue  # Skip unsupported formats
            
            try:
                img = Image.open(image_path)
                img.thumbnail((600, 600))  # Adjusted thumbnail size
            except Exception as e:
                img = None  # Handle unreadable images

            try:
                exif_data = img.getexif() if img else {}
            except Exception as e:
                exif_data = {}

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
                description = description.decode('utf-16-le').strip('\x00')
            if isinstance(keywords, bytes):
                keywords = keywords.decode('utf-16-le').strip('\x00')

            outputs.extend([img, filename, title, description, keywords])
        else:
            outputs.extend([None, '', '', '', ''])
        progress((idx + 1) / 100, desc=f"Processing image {idx + 1} of {num_files}")
    return outputs


def save_metadata(*args):
    data = []
    for i in range(100):
        idx = i * 5
        img = args[idx]  # Not used, but kept for consistency
        filename = args[idx + 1]
        title = args[idx + 2]
        description = args[idx + 3]
        keywords = args[idx + 4]
        if filename:
            data.append({
                'Filename': filename,
                'Title': title,
                'Description': description,
                'Keywords': keywords,
            })
    df = pd.DataFrame(data, columns=['Filename', 'Title', 'Description', 'Keywords'])
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
    gr.Markdown("## Image Metadata Extractor")
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

    # Save Button and Output
    with gr.Row():
        save_button = gr.Button("Save CSV")
        save_output = gr.Textbox(label="Save Status", interactive=False)

    # Collect all output components for extraction and saving
    all_outputs = []
    for i in range(100):
        all_outputs.extend([
            image_components[i],
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

    save_button.click(
        fn=save_metadata,
        inputs=all_outputs,
        outputs=save_output
    )

    # Style adjustments can be further customized as needed

demo.launch()
