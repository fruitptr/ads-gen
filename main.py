import asyncio
import base64
import os
import requests
import uvicorn
import traceback
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import httpx
from openai import OpenAI
from typing import List, Optional
import tempfile
from asyncio import Semaphore
import time
from PIL import Image
import io

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

# Rate limit settings
OPENAI_RATE_LIMIT = 5  # requests per second
rate_limit_semaphore = Semaphore(OPENAI_RATE_LIMIT)
last_request_time = {}

async def process_task(task: Task, product_images: List[ProductImage], callback_url: str, brand_logo: Optional[BrandLogo] = None, inspiration_images: Optional[List[InspirationImage]] = None):
    temp_filepaths = []
    image_file_objects = []
    try:
        # Implement rate limiting
        async with rate_limit_semaphore:
            # Ensure minimum time between requests
            current_time = time.time()
            if task.task_id in last_request_time:
                time_since_last = current_time - last_request_time[task.task_id]
                if time_since_last < 1/OPENAI_RATE_LIMIT:
                    await asyncio.sleep(1/OPENAI_RATE_LIMIT - time_since_last)
            
            last_request_time[task.task_id] = time.time()
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
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
                print("Temp file path: ", temp_file.name)
            
            # Process inspiration images if provided
            if inspiration_images:
                for img in inspiration_images:
                    print(f"Processing inspiration image: {img.name}")
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
        
        if temp_filepaths:
            # Open all images and add them to the image_file_objects list
            for path in temp_filepaths:
                image_file = open(path, "rb")
                image_file_objects.append(image_file)
                
            print("Before calling OpenAI API")

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

            print("Image generated successfully")
        
            # Callback to PHP server using httpx for async HTTP requests
            async with httpx.AsyncClient(timeout=60.0) as client:  # Set 60 seconds timeout
                response = await client.post(
                    callback_url,
                    json={
                        "task_id": task.task_id,
                        "result": image_base64
                    },
                )
        
            print(f"Callback response for task {task.task_id}: Status {response.status_code}")
            print(f"Callback response text: {response.text}")
        else:
            print(f"No product images provided for task {task.task_id}")
    except Exception as e:
        print(f"Error processing task {task.task_id}: {e}")
        traceback.print_exc()
        raise  # Re-raise the exception to help with debugging

    finally:
        # Close file objects
        for f_obj in image_file_objects:
            try:
                f_obj.close()
            except Exception as close_error:
                print(f"Error closing temp file object: {close_error}") # Log closing errors
                
        # Clean up temporary files
        for f_path in temp_filepaths:
            try:
                if os.path.exists(f_path):  # Check if file exists before deleting
                    os.unlink(f_path)
            except Exception as cleanup_error:
                print(f"Failed to delete temp file {f_path}: {cleanup_error}") # Log deletion errors

@app.post("/generate-ai-ads-batch")
async def generate_ai_ads_batch(batch: BatchRequest):
    print(f"PIL available: {Image is not None}")
    tasks = []
    print("Callback URL: ", batch.callback_url)
    print("Product images length: ", len(batch.product_images))
    print("Inspiration images length: ", len(batch.inspiration_images))
    print("Brand logo: ", batch.brand_logo)
    print("Batch tasks length: ", len(batch.tasks))
    for task in batch.tasks:
        # Create tasks but don't start them immediately
        tasks.append(asyncio.create_task(process_task(task, batch.product_images, batch.callback_url, batch.brand_logo, batch.inspiration_images)))
    
    # Return immediately without waiting for tasks to complete
    return {"success": True, "message": f"Batch processing started in background for {len(tasks)} tasks"}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)