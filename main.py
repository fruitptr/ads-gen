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
from asyncio import Semaphore
import time

app = FastAPI()

executor = ThreadPoolExecutor(max_workers=3)

class ProductImage(BaseModel):
    name: str
    type: str
    data: str  # base64

class Task(BaseModel):
    task_id: str
    prompt: str

class BatchRequest(BaseModel):
    callback_url: str
    tasks: List[Task]
    images: Optional[List[ProductImage]] = []

# Rate limit settings
OPENAI_RATE_LIMIT = 5  # requests per second
rate_limit_semaphore = Semaphore(OPENAI_RATE_LIMIT)
last_request_time = {}

async def process_task(task: Task, product_images: List[ProductImage], callback_url: str):
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
            
            for img in product_images:
                img_bytes = base64.b64decode(img.data)
                suffix = ".png" if "png" in img.type else ".jpg"
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(img_bytes)
                temp_file.close()
                temp_filepaths.append(temp_file.name)
                print("Temp file path: ", temp_file.name)
        
        if temp_filepaths:
            with open(temp_filepaths[0], "rb") as base_image:  # Use context manager
                image_file_objects.append(base_image)
                
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: client.images.edit(
                        model="gpt-image-1",
                        image=base_image,
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
        
                print(f"Callback response for task {task.task_id}: Status {response.status_code}")
                print(f"Callback response text: {response.text}")
        else:
            print(f"No product images provided for task {task.task_id}")
    except Exception as e:
        print(f"Error processing task {task.task_id}: {e}")
        raise  # Re-raise the exception to help with debugging

    finally:
        # Clean up temporary files
        for f_path in temp_filepaths:
            try:
                if os.path.exists(f_path):  # Check if file exists before deleting
                    os.unlink(f_path)
            except Exception as cleanup_error:
                print(f"Failed to delete temp file {f_path}: {cleanup_error}") # Log deletion errors

@app.post("/generate-ai-ads-batch")
async def generate_ai_ads_batch(batch: BatchRequest):
    print("Batch: ", batch)
    tasks = []
    for task in batch.tasks:
        # Create tasks but don't start them immediately
        tasks.append(asyncio.create_task(process_task(task, batch.images, batch.callback_url)))
    
    # Return immediately without waiting for tasks to complete
    return {"success": True, "message": f"Batch processing started in background for {len(tasks)} tasks"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)