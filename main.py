import asyncio
import base64
import os
import requests
import uvicorn
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import httpx
from openai import OpenAI
from typing import List, Optional
import tempfile

app = FastAPI()

executor = ThreadPoolExecutor(max_workers=3)

class ProductImage(BaseModel):
    name: str
    type: str
    data: str  # base64

class InspirationImage(BaseModel):
    name: str
    type: str
    data: str  # base64

class BrandLogo(BaseModel):
    name: str
    type: str
    data: str  # base64

class Task(BaseModel):
    task_id: str
    prompt: str

class BatchRequest(BaseModel):
    callback_url: str
    tasks: List[Task]
    product_images: Optional[List[ProductImage]] = []
    inspiration_images: Optional[List[InspirationImage]] = []
    brand_logo: Optional[BrandLogo] = None

async def process_task(task: Task, product_images: List[ProductImage], callback_url: str, brand_logo: Optional[BrandLogo] = None):
    temp_filepaths = []
    image_file_objects = []
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        from PIL import Image
        import io

        def convert_image_format(image_bytes, original_format, target_format):
            with Image.open(io.BytesIO(image_bytes)) as img:
                with io.BytesIO() as output:
                    img.convert("RGB").save(output, format=target_format)
                    return output.getvalue()

        for img in product_images:
            print(f"Processing product image: {img.name}")
            img_bytes = base64.b64decode(img.data)
            original_format = img.type.split('/')[-1]
            target_format = "PNG" if original_format in ["webp", "avif"] else original_format.upper()
            converted_bytes = convert_image_format(img_bytes, original_format, target_format)
            suffix = f".{target_format.lower()}"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(converted_bytes)
            temp_file.close()
            temp_filepaths.append(temp_file.name)

        # Process brand logo if provided
        if brand_logo:
            print(f"Processing brand logo: {brand_logo.name}")
            logo_bytes = base64.b64decode(brand_logo.data)
            original_format = brand_logo.type.split('/')[-1]
            target_format = "PNG" if original_format in ["webp", "avif"] else original_format.upper()
            converted_bytes = convert_image_format(logo_bytes, original_format, target_format)
            suffix = f".{target_format.lower()}"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(converted_bytes)
            temp_file.close()
            temp_filepaths.append(temp_file.name)

        # The API expects a list of image files
        if temp_filepaths:
            # Open all images and add them to the image_file_objects list
            for path in temp_filepaths:
                image_file = open(path, "rb")
                image_file_objects.append(image_file)

            # OpenAI API call - using all images
            # Run CPU-bound operations in a thread pool to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.images.edit(
                    model="gpt-image-1",
                    image=image_file_objects,  # Pass a list of file objects
                    prompt=task.prompt,
                )
            )


            image_base64 = result.data[0].b64_json

            # Callback to PHP server using httpx for async HTTP requests
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    callback_url,
                    json={
                        "task_id": task.task_id,
                        "result": image_base64
                    },
                )
            

            # Print the response status code and text
            print(f"Callback response for task {task.task_id}: Status {response.status_code}")
            print(f"Callback response text: {response.text}")
        else:
            print(f"No product images provided for task {task.task_id}")
    except Exception as e:
        print(f"Error processing task {task.task_id}: {e}")

    finally:
        for f_obj in image_file_objects:
            try:
                f_obj.close()
            except Exception as close_error:
                print(f"Error closing temp file object: {close_error}") # Log closing errors

        for f_path in temp_filepaths:
            try:
                os.unlink(f_path)
            except Exception as cleanup_error:
                print(f"Failed to delete temp file {f_path}: {cleanup_error}") # Log deletion errors

@app.post("/generate-ai-ads-batch")
async def generate_ai_ads_batch(batch: BatchRequest):
    # Create background tasks without waiting for them to complete
    for task in batch.tasks:
        # Schedule the task to run in the background
        asyncio.create_task(process_task(task, batch.product_images, batch.callback_url, batch.brand_logo))
        # Add a delay between each task to prevent overloading
        await asyncio.sleep(2)
    
    # Return immediately without waiting for tasks to complete
    return {"success": True, "message": "Batch processing started in background."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)