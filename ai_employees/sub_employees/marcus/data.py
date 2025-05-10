from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
from zoneinfo import ZoneInfo
import base64
import requests
from io import BytesIO
import os
import asyncio
import time
import tempfile
import traceback
from asyncio import Semaphore
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from PIL import Image
import io

from ai_employees.sub_employees.data import EmployeeDataHolder

day_abbr_to_iso = {
    "Mon": 1,
    "Tue": 2,
    "Wed": 3,
    "Thu": 4,
    "Fri": 5,
    "Sat": 6,
    "Sun": 7
}

# Rate limit settings
OPENAI_RATE_LIMIT = 5  # requests per second
rate_limit_semaphore = Semaphore(OPENAI_RATE_LIMIT)
last_request_time = {}


@dataclass(frozen=True)
class MarcusDataHolder(EmployeeDataHolder):
    ads_per_day: int
    ad_guidance: str
    product_url: str
    product_image_url: str
    run_days: List[str]

    @staticmethod
    def from_dict(configuration: dict):
        return MarcusDataHolder(
            ads_per_day=configuration.get('adsPerDay', 0),
            ad_guidance=configuration.get('adGuidance', ''),
            product_url=configuration.get('productUrl', ''),
            product_image_url=configuration.get('productImageUrl', ''),
            run_days=configuration.get('days')
        )

    def is_run_able(self) -> bool:
        try:
            current_day = dt.utcnow().isoweekday()
            for day in self.run_days:
                if current_day == day_abbr_to_iso.get(day, 1):
                    return True
            return False
        except Exception as e:
            print("Error in is run able: ", e)
            return False

    def execute(self):
        try:
            print(f"Product URL: {self.product_url}")
            print(f"Product Image URL: {self.product_image_url}")
            
            # Create output directory if it doesn't exist
            output_dir = "generated_ads"
            os.makedirs(output_dir, exist_ok=True)
            
            # Download and save the image
            response = requests.get(self.product_image_url)
            if response.status_code != 200:
                print(f"Failed to download image: {response.status_code}")
                raise Exception("Failed to download image")
            print("Image downloaded successfully.")
            
            # Save the downloaded image temporarily to ensure proper format
            temp_image_path = os.path.join(output_dir, "temp_source_image.png")
            with open(temp_image_path, "wb") as f:
                f.write(response.content)
            print(f"Saved temporary image to {temp_image_path}")
            
            # Convert to async function for parallel processing
            async def generate_ad(i):
                temp_filepaths = []
                image_file_objects = []
                try:
                    # Implement rate limiting
                    async with rate_limit_semaphore:
                        # Ensure minimum time between requests
                        task_id = f"ad_{i}"
                        current_time = time.time()
                        if task_id in last_request_time:
                            time_since_last = current_time - last_request_time[task_id]
                            if time_since_last < 1/OPENAI_RATE_LIMIT:
                                await asyncio.sleep(1/OPENAI_RATE_LIMIT - time_since_last)
                        
                        last_request_time[task_id] = time.time()
                        
                        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                        
                        # Basic prompt for the ad
                        prompt = f"Create a professional advertisement for this product. {self.ad_guidance}"
                        
                        # Open the image file
                        image_file = open(temp_image_path, "rb")
                        image_file_objects.append(image_file)
                        temp_filepaths.append(temp_image_path)
                        
                        print(f"Before calling OpenAI API for ad {i+1}")
                        print(f"Prompt: {prompt}")
                        
                        loop = asyncio.get_running_loop()
                        
                        # Retry logic for image generation
                        max_retries = 5
                        retry_delay = 4  # seconds
                        result = None
                        last_error = None
                        
                        for attempt in range(max_retries):
                            try:
                                result = await loop.run_in_executor(
                                    None,
                                    lambda: client.images.edit(
                                        model="gpt-image-1",
                                        image=image_file_objects,  # Pass a list of file objects
                                        prompt=prompt,
                                        size="auto",
                                    )
                                )
                                # If successful, break out of the retry loop
                                break
                            except Exception as e:
                                last_error = e
                                print(f"Attempt {attempt+1}/{max_retries} failed for ad {i+1}: {e}")
                                if attempt < max_retries - 1:  # Don't sleep after the last attempt
                                    print(f"Retrying in {retry_delay} seconds...")
                                    await asyncio.sleep(retry_delay)
                                    # Reopen file objects for the next attempt
                                    for f_obj in image_file_objects:
                                        f_obj.close()
                                    image_file_objects = []
                                    image_file = open(temp_image_path, "rb")
                                    image_file_objects.append(image_file)
                        
                        # If all retries failed, raise the error
                        if result is None:
                            error_message = str(last_error)
                            print(f"All retries failed for ad {i+1}: {error_message}")
                            raise Exception(f"Failed to generate ad after {max_retries} attempts: {error_message}")
                        
                        # Get the image data
                        image_base64 = result.data[0].b64_json
                        image_bytes = base64.b64decode(image_base64)
                        
                        # Generate a unique filename
                        timestamp = dt.now().strftime("%Y%m%d%H%M%S")
                        filename = f"ad_{timestamp}_{i}.png"
                        filepath = os.path.join(output_dir, filename)
                        
                        # Save the image
                        with open(filepath, "wb") as f:
                            f.write(image_bytes)
                        
                        print(f"Generated ad {i+1}/{self.ads_per_day}: {filepath}")
                        return True
                except Exception as e:
                    print(f"Error generating ad {i+1}: {str(e)}")
                    traceback.print_exc()
                    return False
                finally:
                    # Close file objects
                    for f_obj in image_file_objects:
                        try:
                            f_obj.close()
                        except Exception as close_error:
                            print(f"Error closing temp file object: {close_error}")
            
            # Create and run tasks in parallel
            async def run_all_tasks():
                tasks = []
                for i in range(int(self.ads_per_day)):
                    tasks.append(generate_ad(i))
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Count successful generations
                successful = sum(1 for result in results if result)
                print(f"Ad generation complete. Successfully generated {successful}/{self.ads_per_day} ads.")
            
            # Run the async tasks
            asyncio.run(run_all_tasks())
            
            # Clean up the temporary file
            if os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                except Exception as e:
                    print(f"Failed to delete temp file {temp_image_path}: {e}")
                
        except Exception as e:
            print("Error in execute: ", e)
            traceback.print_exc()
