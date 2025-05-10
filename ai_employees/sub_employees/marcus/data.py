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
import re
import json
from anthropic import Anthropic
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

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
            
    def generate_ad_ideas(self):
        """
        Generate ad ideas based on the product URL's HTML content using Anthropic API.
        Returns a list of ad ideas.
        """
        try:
            print(f"Generating ad ideas for product URL: {self.product_url}")
            
            # Fetch HTML content from the product URL
            product_html = ''
            if self.product_url:
                try:
                    proxy_one = os.getenv('proxy_one')
                    proxy_two = os.getenv('proxy_two')
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    # Proxy configuration
                    proxies = {
                        'http': proxy_one,
                        'https': proxy_two
                    }
                    
                    response = requests.get(
                        self.product_url, 
                        headers=headers, 
                        proxies=proxies,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        product_html = response.text
                        print(f"Successfully fetched HTML content from {self.product_url}")
                    else:
                        print(f"Failed to fetch HTML content: {response.status_code}")
                except Exception as e:
                    print(f"Error fetching product URL: {str(e)}")
            
            # Clean HTML content
            if product_html:
                # Remove script tags and their content
                product_html = re.sub(r'<script(.*?)>(.*?)</script>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<style(.*?)>(.*?)</style>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<svg(.*?)>(.*?)</svg>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<link(.*?)>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<noscript(.*?)>(.*?)</noscript>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<iframe(.*?)>(.*?)</iframe>', '', product_html, flags=re.DOTALL)
                product_html = re.sub(r'<div\b[^>]*>\s*</div>', '', product_html, flags=re.DOTALL)
                
                # Trim HTML content if it's too long to avoid token limits
                if len(product_html) > 100000:
                    product_html = product_html[:100000] + "... [content truncated for token limit]"

            print("Product HTML content cleaned successfully")

            # Construct the prompt for ad ideas
            ad_ideas_prompt = f"""You are an expert marketing consultant and creative director + strategist. This is for an ai ad image generator. Create {self.ads_per_day} unique and compelling ad concepts"""
            
            if self.ad_guidance:
                ad_ideas_prompt += f". Consider this guidance: {self.ad_guidance}"

            ad_ideas_prompt += f'''
                
                Here is the html content of the product page:
                {product_html}
                

                FIRST STEP: extract the following information from the html content:
                - Product Title
                - Description
                - Price (if available)
                - Key Features (bullet points)
                - Key benefits (bullet points)
                - Key selling points (bullet points)
                - Brand identity, colors, fonts, make a very big report on the brand identity so we have info about the style of the ad.
                - Any additional relevant details.

               
                Use this information to inform your ad concepts.

                IMPORTANT: Your response must follow this exact structure for each ad idea, the content of the ad idea should be in English, numbered from 1 to {self.ads_per_day}:

                Ad Idea [number]:
                1. Headline: [Attention-grabbing headline]
                2. Main Message: [Core value proposition in 1-2 sentences]
                3. Visual Description: [Clear description of the proposed visuals]
                4. Call to Action: [Compelling CTA]
                5. Emotional Appeal: [Primary emotion targeted]
                6. Brand identity: [brand identity, colors, fonts, make a very big report on the brand identity so we have info about the style of the ad.]

                Context:
                - These ad ideas will be used for an ai image advertisement.
                - These ads will not be videos.
                - The ad will be a single image.
                - Use knowledge from the book 'breakthrough advertising' by Gary Halbert.

                Critical requirements:
                - Format exactly as shown above
                - Be specific and actionable
                - Premium Design - Polished, professional look with a single, brand-appropriate background color unless client requests otherwise.
                - Only use humans in the advertisement if it makes sense for the ad, if you do use them make sure they are not the main focus of the ad.
                - For fashion items prefer the use of models/humans in the ad. Because customers want to see how the product looks on a real person.
                - Focus on benefits over features
                - Make sure the subject of the ad is focussed on something that matters. Example: the product that you extracted can maybe highlight unique selling points like sleek design, but this should not be the main focus of the ad and we should not make the whole ad about the product having a sleek design, it's only a benefit you might want to include.
                - For the subject think about what the product does and think of usecases and benefits. It is best if you directly make the ad tailored to a specific benefit. So if the product is an earplug and you found it can be targetted at festival goers, you can make the ad about that.
                - Keep language clear and compelling, make sure the copy makes sense and is not too abstract.
                - Make each ad unique and distinct
                - Ensure CTAs are strong and specific
                - DO NOT include any introductory text, explanations, or conclusions
                - Start directly with 'Ad Idea 1:' and end with the last ad idea
                - Think about who the target audience is and only use language they would use
                - If the product is a nutrition product, you can think of an ad idea that includes either (or combined): ingredients and benefits of those ingredients, a testimonial from a satisfied customer (because customers are sceptical of nutrition products without a testimonial- cause you dont know if it works from just the ad, so a testimonial is as close as you can get to a referral). ONLY INCLUDE ANY OF THESE IF YOU ACTUALLY HAVE THE INFORMATION TO INCLUDE, DO NOT FILL IN INFORMATION IF YOU DO NOT HAVE THE INFORMATION.
                
                Position the product as the apple of it's product category.
                
                If branding is not clear, think of a big brand in the same product category and use similar branding.
                
                Try to avoid em dashes in ads. Avoid big chunks of text in one place.
                
                We will be running this prompt on similar inputs multiple times, but we do not want the same output. Add some variation while keeping the same quality.
                Do not include any introductory text, explanations, or conclusions in your response or Information Extracted from Content in the response text.
            '''

            print("Ad ideas prompt constructed successfully")
            
            anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            response = anthropic_client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=20000,
                messages=[
                    {
                        "role": "user",
                        "content": ad_ideas_prompt
                    }
                ]
            )
            print("Response received from Anthropic API")
            
            # Extract the content from the response
            content = response.content[0].text
            
            # Process the response into structured ideas
            raw_ideas = re.split(r'(?=Ad Idea \d+:)', content)
            
            # Remove empty first element if exists
            if raw_ideas and not raw_ideas[0].strip():
                raw_ideas.pop(0)
            
            # Trim whitespace from each idea
            ideas = [idea.strip() for idea in raw_ideas]
            
            print(f"Generated {len(ideas)} ad ideas")
            return ideas
            
        except Exception as e:
            print(f"Error generating ad ideas: {str(e)}")
            traceback.print_exc()
            return []

    def execute(self):
        try:
            print(f"Product URL: {self.product_url}")
            print(f"Product Image URL: {self.product_image_url}")
            
            # Create output directory if it doesn't exist
            output_dir = "temp_images"
            os.makedirs(output_dir, exist_ok=True)
            
            # First, generate ad ideas based on the product URL
            ad_ideas = self.generate_ad_ideas()
            
            if not ad_ideas:
                print("No ad ideas were generated. Using default approach.")
                ad_count = int(self.ads_per_day)
            else:
                print(f"Successfully generated {len(ad_ideas)} ad ideas")
                ad_count = len(ad_ideas)
            
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
            
            async def generate_ad(i, ad_idea=None):
                temp_filepaths = []
                image_file_objects = []
                try:
                    async with rate_limit_semaphore:
                        task_id = f"ad_{i}"
                        current_time = time.time()
                        if task_id in last_request_time:
                            time_since_last = current_time - last_request_time[task_id]
                            if time_since_last < 1/OPENAI_RATE_LIMIT:
                                await asyncio.sleep(1/OPENAI_RATE_LIMIT - time_since_last)
                        
                        last_request_time[task_id] = time.time()
                        
                        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                        
                        if ad_idea:

                            prompt = f'''**SYSTEM (role & mindset)**  
                                You are an *award-winning senior social-media art-director & copy-chief* hired to craft turnkey **paid-media image ads** that convert.
                                You can make ads that are the highest quality, most engaging, and most effective ads that are possible. If the product is high-end you will make sure to make ads that follow all rules of high-end ads for example.
                                All your ads will be in aspect ratio 1:1 so 1024x1024px.
                                ---

                                ## 1 INPUTS  
                                * **Campaign Idea / Objective ** - {ad_idea}
                                * **Client Guidance:** - {self.ad_guidance}  
                                * **Language ** - English

                                ---

                                ## VERY IMPORTANT
                                - DO not change the product referenced. Not the color, not the font on it, not the packaging, change nothing about the product referenced. Do not change the product colors or packaging to match the color scheme you have in mind, rather change the color scheme of the whole ad to match the product. So if the product is a coffee product with shiny purple packaging, and the image needs to have colors in harmony, do not change the color of the packaging to brown because the background of the ad is also brown and it matches 'coffee'. No, you should keep the product in the referenced image the same, and you can tweak your color scheme of the ad image to match the product. Conclusion: Do not change the product referenced to match the color scheme, match the color scheme to the product reference.

                                ## 2 NON-NEGOTIABLES  
                                1. **Accuracy** - Use only information explicitly supplied; no hallucinated features or claims. The product image should match the image of the product that is attached precisely. DO NOT CHANGE THE COLORS.  
                                2. **Audience Insight** - If not specified, infer the most probable buyer persona (demographic + psychographic).  
                                3. **Language** - Think *natively* in the given input language; flawless spelling, grammar, punctuation.  
                                4. **Premium Design** - Polished, professional look with a **single, brand-appropriate background color** unless client requests otherwise.  
                                5. **Do not change the product colors or packaging to match the color scheme you have in mind, but change the color scheme of the whole image to match the product.**
                                6. **Image-Generation Safeguards**  
                                * Limit on-image copy to **≤ 6 words** per block; avoid long paragraphs.  
                                * **Centered composition** with at least **15 % safe margin** on every side so no text is cropped.  
                                * Specify exact **brand palette (HEX/CMYK)**; do not alter product colors or packaging.  
                                * Include **negative prompts**: no extraneous objects, no unwanted text, no distortions.  
                                * Prefer product-focused mid-shots; minimal faces/hands to avoid anatomical glitches.  
                                7. **Aspect Ratio** - The aspect-ratio must be 1 : 1. Do not change the aspect ratio after generation. And do not crop out text or important elements of the image.
                                8. **Compliance** - Follow Meta, FTC, and local ad policies; no exaggerated, medical, or unverifiable claims.

                                ---

                                ## 3 OUTPUT SPECIFICATIONS  
                                Return **one** clean Markdown block in the exact structure below—nothing else.

                                ### Ad Copy Directions  
                                - **Headline:** A sharp, benefit-driven hook (≤ 6 words).  
                                - **Benefits:** *(optional)* Bullet key outcomes or problem-solving points.  
                                - **Social Proof:** *(optional)* One short customer quote.

                                ### Visual Prompt for AI Image Generator  
                                Describe one premium scene including:  
                                • Subject & setting • Camera angle/style • **Single-color background** (specify HEX/CMYK) • Lighting • Mood  
                                • Composition note: centered, 15 % safe margins
                                • The client guidance can overwrite any of the above instructions
                                • **Negative prompts:** no extraneous objects, no unwanted text, no distortions
                                - **Product:** Must match supplied reference exactly—colors, text, packaging, all details.  
                                - **Optional layering:** Background shapes/elements may be subtly layered (Canva/Photoshop style) as long as product remains hero.

                                ### Compliance Confirmation  
                                Confirmed: content adheres to Meta advertising rules and all relevant regulations.'''
                        else:
                            print("Ad idea not provided. Using default prompt.")
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
                                        size="1024x1024",
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
                        timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
                        file_name = f"ad_{i+1}_{timestamp}.png"
                        
                        content_type = 'image/png'
                        r2_url = self.upload_image_to_r2(image_base64, file_name, content_type)
                        
                        if r2_url:
                            print(f"Successfully uploaded ad {i+1} to R2: {r2_url}")
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
                for i in range(ad_count):
                    # Pass the corresponding ad idea if available
                    ad_idea = ad_ideas[i] if i < len(ad_ideas) else None
                    tasks.append(generate_ad(i, ad_idea))
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks)
                
                # Count successful generations
                successful = sum(1 for result in results if result)
                print(f"Ad generation complete. Successfully generated {successful}/{ad_count} ads.")
            
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

    def upload_image_to_r2(self, image_data, file_name, content_type='image/png'):
        try:
            endpoint = os.getenv("R2_ENDPOINT")
            access_key = os.getenv("R2_ACCESS_KEY")
            secret_key = os.getenv("R2_SECRET_KEY")
            public_url = os.getenv("R2_PUBLIC_URL")
            bucket = 'ai-ugc-test'
            folder = 'ai-ads-gen/' + content_type.replace('/', '-')
            
            file_path = f"{folder}/{file_name}"
            
            if isinstance(image_data, str) and image_data.startswith(('data:image', 'iVBOR')):
                if ',' in image_data:
                    image_data = image_data.split(',', 1)[1]
                image_content = base64.b64decode(image_data)
            else:
                image_content = image_data
            
            s3_client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'
            )
            
            try:
                result = s3_client.put_object(
                    Bucket=bucket,
                    Key=file_path,
                    Body=image_content,
                    ContentType=content_type,
                    ACL='public-read'
                )
                
                public_object_url = f"{public_url}/{bucket}/{file_path}"
                print(f"Public URL: {public_object_url}")
                
                return public_object_url
            except ClientError as e:
                print(f"R2 S3 Exception: {str(e)}")
                return None
        except Exception as e:
            print(f"R2 Upload Exception: {str(e)}")
            traceback.print_exc()
            return None
