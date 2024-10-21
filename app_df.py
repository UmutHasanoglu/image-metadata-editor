import gradio as gr
from PIL import Image, ExifTags
import pandas as pd
import os

def extract_metadata(uploaded_files):
    data = []
    for image_path in uploaded_files:
        filename = os.path.basename(image_path)  # Get the original filename
        try:
            img = Image.open(image_path)
            exif_data = img.getexif()
        except Exception as e:
            # Handle images that cannot be opened or have no EXIF data
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

        if isinstance(title, bytes):
            title = title.decode('utf-16-le').strip('\x00')
        if isinstance(description, bytes):
            description = description.decode('utf-16-le').strip('\x00')
        if isinstance(keywords, bytes):
            keywords = keywords.decode('utf-16-le').strip('\x00')

        data.append({
            'Filename': filename,
            'Title': title,
            'Description': description,
            'Keywords': keywords,
        })

    df = pd.DataFrame(data, columns=['Filename', 'Title', 'Description', 'Keywords'])
    return df

def save_dataframe(dataframe):
    # Convert the data received from Gradio Dataframe component to pandas DataFrame
    df = pd.DataFrame(dataframe, columns=['Filename', 'Title', 'Description', 'Keywords'])
    try:
        df.to_csv('edited_metadata.csv', index=False)
        return "Data saved successfully to 'edited_metadata.csv'!"
    except Exception as e:
        return f"Error saving data: {e}"

with gr.Blocks(css="""
    .gr-dataframe {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto !important;
    }
    .gr-file {
        width: 100% !important;
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
    output_df = gr.Dataframe(
        headers=["Filename", "Title", "Description", "Keywords"],
        interactive=True,  # Make the dataframe editable
        wrap=True
    )
    save_button = gr.Button("Save CSV")
    save_output = gr.Textbox(label="Save Status", interactive=False)
    
    extract_button.click(fn=extract_metadata, inputs=file_input, outputs=output_df)
    save_button.click(fn=save_dataframe, inputs=output_df, outputs=save_output)

demo.launch()
