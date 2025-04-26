import asyncio
import base64
import io
import requests
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

class Task(BaseModel):
    task_id: str
    prompt: str

class BatchRequest(BaseModel):
    api_key: str
    callback_url: str
    tasks: List[Task]
    product_images: Optional[List[ProductImage]] = []
    inspiration_images: Optional[List[InspirationImage]] = []

def process_task(task: Task, product_images: List[ProductImage], callback_url: str, api_key: str):
    try:
        client = OpenAI(api_key=api_key)

        # Create real temp files for each image
        temp_filepaths = []
        for img in product_images:
            img_bytes = base64.b64decode(img.data)
            suffix = ".png" if "png" in img.type else ".jpg"  # crude mimetype check
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(img_bytes)
            temp_file.close()
            temp_filepaths.append(temp_file.name)

        # Open file objects for OpenAI
        image_files = [open(path, "rb") for path in temp_filepaths]

        # OpenAI API call
        result = client.images.edit(
            model="gpt-image-1",
            image=image_files,
            prompt=task.prompt,
        )

        image_base64 = result.data[0].b64_json

        # Callback to PHP server
        requests.post(callback_url, json={
            "task_id": task.task_id,
            "result": image_base64
        })

    except Exception as e:
        print(f"Error processing task {task.task_id}: {e}")

    finally:
        # Always cleanup temp files
        for f in temp_filepaths:
            try:
                import os
                os.unlink(f)
            except Exception as cleanup_error:
                print(f"Failed to delete temp file {f}: {cleanup_error}")

        for f in image_files:
            try:
                f.close()
            except:
                pass

@app.post("/generate-ai-ads-batch")
async def generate_ai_ads_batch(batch: BatchRequest):
    event_loop = asyncio.get_event_loop()    
    for task in batch.tasks:
        event_loop.run_in_executor(executor, process_task, task, batch.product_images, batch.callback_url, batch.api_key)
    return {"success": True, "message": "Batch processing started."}