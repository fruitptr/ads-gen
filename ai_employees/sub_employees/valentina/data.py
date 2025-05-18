from typing import Dict, Any
from dataclasses import dataclass
import requests
import tempfile
import os
from datetime import datetime as dt
from openai import OpenAI
import io
import asyncio
import time
import traceback
from asyncio import Semaphore

from ai_employees.sub_employees.data import EmployeeDataHolder


# Rate limit settings
OPENAI_RATE_LIMIT = 5  # requests per second
rate_limit_semaphore = Semaphore(OPENAI_RATE_LIMIT)
last_request_time = {}


@dataclass(frozen=True)
class ValentinaDataHolder(EmployeeDataHolder):
    custom: str
    spell: bool
    grammar: bool
    visuals: bool
    claims: bool
    copyright: bool
    policy: bool
    offensive: bool
    layout: bool
    faces: bool
    cta: bool
    multi_lang: bool
    prompt: bool
    over_promise: bool

    @staticmethod
    def from_dict(configuration: Dict[str, Any]):
        return ValentinaDataHolder(
            custom=configuration.get('custom', ''),
            spell=configuration.get('spell', False),
            grammar=configuration.get('grammar', False),
            visuals=configuration.get('visuals', False),
            claims=configuration.get('claims', False),
            copyright=configuration.get('copyright', False),
            policy=configuration.get('policy', False),
            offensive=configuration.get('offensive', False),
            layout=configuration.get('layout', False),
            faces=configuration.get('faces', False),
            cta=configuration.get('cta', False),
            multi_lang=configuration.get('multiLang', False),
            prompt=configuration.get('prompt', False),
            over_promise=configuration.get('overpromise', False)
        )

    def is_run_able(self) -> bool:
        return True

    def execute(self, userid, connection):
        if not connection:
            print("No database connection available")
            return
        
        cursor = connection.cursor()
        try:
            # Fetch all unevaluated images for this user
            query = """
                SELECT id, image_url FROM employee_ai_ads_images 
                WHERE userid = %s AND is_evaluated = 0
            """
            cursor.execute(query, (userid,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"No unevaluated images found for user {userid}")
                return
            
            print(f"Found {len(rows)} unevaluated images for user {userid}")
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            async def process_image(row_id, image_url):
                temp_image_path = None
                image_file_objects = []
                
                try:
                    async with rate_limit_semaphore:
                        task_id = f"img_{row_id}"
                        current_time = time.time()
                        if task_id in last_request_time:
                            time_since_last = current_time - last_request_time[task_id]
                            if time_since_last < 1/OPENAI_RATE_LIMIT:
                                await asyncio.sleep(1/OPENAI_RATE_LIMIT - time_since_last)
                        
                        last_request_time[task_id] = time.time()
                    
                    print(f"Processing image ID {row_id} with URL: {image_url}")
                    
                    prompt = f"Please analyze the image for the following issues. Give answer in the form of 'Fix this issue: <issue>' for each issue. If the image is good, just say 'Good image'."
                    if self.custom:
                        prompt += f"\nCustom: {self.custom}"
                    if self.spell:
                        prompt += "\nSpell check"
                    if self.grammar:
                        prompt += "\nGrammar check"
                    if self.visuals:
                        prompt += "\nVisuals check"
                    if self.claims:
                        prompt += "\nClaims check"
                    if self.copyright:
                        prompt += "\nCopyright check"
                    if self.policy:
                        prompt += "\nPolicy check"
                    if self.offensive:
                        prompt += "\nOffensive content check"
                    if self.layout:
                        prompt += "\nLayout check"
                    if self.faces:
                        prompt += "\nFaces check"
                    if self.cta:
                        prompt += "\nCall to action check"
                    if self.multi_lang:
                        prompt += "\nMulti-language check"
                    if self.prompt:
                        prompt += "\nPrompt check"
                    if self.over_promise:
                        prompt += "\nOverpromise check"
                    
                    loop = asyncio.get_running_loop()
                    analysis_response = await loop.run_in_executor(
                        None,
                        lambda: client.responses.create(
                            model="gpt-4.1-mini",
                            input=[{
                                "role": "user",
                                "content": [
                                    {"type": "input_text", "text": prompt},
                                    {
                                        "type": "input_image",
                                        "image_url": image_url,
                                    },
                                ],
                            }],
                        )
                    )
                    
                    analysis_result = analysis_response.output_text
                    print(f"Analysis result for image {row_id}: {analysis_result}")
                    
                    response = await loop.run_in_executor(
                        None,
                        lambda: requests.get(image_url)
                    )
                    
                    if response.status_code != 200:
                        print(f"Failed to download image {row_id}: {response.status_code}")
                        return False
                    
                    temp_image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
                    with open(temp_image_path, "wb") as f:
                        f.write(response.content)
                    
                    image_file = open(temp_image_path, "rb")
                    image_file_objects.append(image_file)
                    
                    fix_prompt = f"Fix the provided image with the following: {analysis_result}"
                    
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
                                    image=image_file_objects,
                                    prompt=fix_prompt,
                                    size="1024x1024",
                                )
                            )
                            # If successful, break out of the retry loop
                            break
                        except Exception as e:
                            last_error = e
                            print(f"Attempt {attempt+1}/{max_retries} failed for image {row_id}: {e}")
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
                        print(f"All retries failed for image {row_id}: {error_message}")
                        return False
                    
                    # Upload the fixed image to R2
                    image_base64 = result.data[0].b64_json
                    timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
                    file_name = f"fixed_ad_{row_id}_{timestamp}.png"
                    
                    content_type = 'image/png'
                    from ai_employees.utils import utils
                    r2_url = utils.upload_image_to_r2(image_base64, file_name, content_type)
                    
                    if r2_url:
                        print(f"Successfully uploaded fixed image to R2: {r2_url}")
                        
                        # Update the database with the new image URL and mark as evaluated
                        update_query = """
                            UPDATE employee_ai_ads_images 
                            SET image_url = %s, is_evaluated = 1 
                            WHERE id = %s
                        """
                        cursor.execute(update_query, (r2_url, row_id))
                        connection.commit()
                        print(f"Updated database record for image ID {row_id}")
                        return True
                    else:
                        print(f"Failed to upload fixed image to R2 for image ID {row_id}")
                        return False
                
                except Exception as e:
                    print(f"Error processing image ID {row_id}: {str(e)}")
                    traceback.print_exc()
                    return False
                
                finally:
                    # Close file objects
                    for f_obj in image_file_objects:
                        try:
                            f_obj.close()
                        except Exception as close_error:
                            print(f"Error closing temp file object: {close_error}")
                    
                    # Clean up the temporary file
                    if temp_image_path and os.path.exists(temp_image_path):
                        try:
                            os.remove(temp_image_path)
                        except Exception as e:
                            print(f"Failed to delete temp file {temp_image_path}: {e}")
            
            # Create and run tasks in parallel
            async def run_all_tasks():
                tasks = []
                for row in rows:
                    row_id, image_url = row
                    tasks.append(process_image(row_id, image_url))
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Count successful evaluations
                successful = sum(1 for result in results if result)
                print(f"Image evaluation complete. Successfully processed {successful}/{len(rows)} images.")
            
            # Run the async tasks
            asyncio.run(run_all_tasks())
            
        except Exception as e:
            print(f"Database error: {str(e)}")
            traceback.print_exc()
        
        finally:
            cursor.close()
