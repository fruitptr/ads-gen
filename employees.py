from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
import base64
import tempfile
import os
import httpx
from openai import OpenAI
import asyncio
from PIL import Image
import io

app = FastAPI()

# Initialize OpenAI client
client = OpenAI()

class ValidationResponse(BaseModel):
    is_valid: bool
    explanation: str

class QualityAssurance:
    @staticmethod
    async def validate_image_with_openai(image_path: str, prompt: str) -> dict:
        """
        Use OpenAI's Vision model to validate if an image is appropriate for advertisement.
        
        Args:
            image_path: Path to the image file
            prompt: Custom prompt for validation criteria
            
        Returns:
            Dictionary with validation results
        """
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            if not prompt:
                prompt = "Is this image appropriate for an advertisement? Please check for quality, offensive content, and commercial viability. Explain your reasoning."
                
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
            )
            
            result_text = response.choices[0].message.content
            
            # Determine if the image is valid based on the response
            is_valid = "yes" in result_text.lower() or "appropriate" in result_text.lower()
            if "not appropriate" in result_text.lower() or "inappropriate" in result_text.lower():
                is_valid = False
                
            return {
                "is_valid": is_valid,
                "explanation": result_text
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "explanation": f"Error during validation: {str(e)}"
            }

    @staticmethod
    async def process_uploaded_image(image: UploadFile) -> str:
        """
        Process an uploaded image and save it to a temporary file.
        
        Args:
            image: The uploaded image file
            
        Returns:
            Path to the temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{image.filename.split('.')[-1]}")
        
        try:
            contents = await image.read()
            temp_file.write(contents)
            temp_file.close()
            return temp_file.name
        except Exception as e:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/validate-ad-image", response_model=ValidationResponse)
async def validate_ad_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """
    Endpoint to validate if an uploaded image is appropriate for advertisement.
    
    Args:
        image: The image file to validate
        prompt: Custom prompt for validation criteria (optional)
        
    Returns:
        ValidationResponse with validation results
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image")
    
    temp_filepath = None
    try:
        temp_filepath = await QualityAssurance.process_uploaded_image(image)
        result = await QualityAssurance.validate_image_with_openai(temp_filepath, prompt)
        
        return ValidationResponse(
            is_valid=result["is_valid"],
            explanation=result["explanation"]
        )
    
    finally:
        # Clean up temporary file
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.unlink(temp_filepath)
            except Exception as e:
                print(f"Failed to delete temp file {temp_filepath}: {e}")


class AdCreator:
    """
    Class for creating advertisement images by sending data to the WinningHunter API.
    """
    
    @staticmethod
    async def create_ad_images(
        product_image: UploadFile,
        product_url: str,
        ad_count: int,
        brand_logo: Optional[UploadFile] = None,
    ) -> dict:
        """
        Create advertisement images by sending data to the WinningHunter API.
        
        Args:
            product_image: The product image file
            product_url: URL of the product
            ad_count: Number of ad variations to generate
            brand_logo: Optional brand logo image file
            
        Returns:
            dict: API response data
        """
        if not product_image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Product file is not an image")
            
        if brand_logo and not brand_logo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Brand logo file is not an image")
        
        # Process uploaded files
        temp_filepaths = []
        files = {}
        
        try:
            # Process product image
            product_image_path = await QualityAssurance.process_uploaded_image(product_image)
            temp_filepaths.append(product_image_path)
            files["product_image"] = open(product_image_path, "rb")
            
            # Process brand logo if provided
            if brand_logo:
                brand_logo_path = await QualityAssurance.process_uploaded_image(brand_logo)
                temp_filepaths.append(brand_logo_path)
                files["brand_logo"] = open(brand_logo_path, "rb")
            
            # Prepare form data
            data = {
                "accountId": "act_1060735341757490",
                "pageId": "131443420055366",
                "pageAccessToken": "EAA54wq88oVMBOztN0GZCdZAQrk3ZAlUKLQBZCXQdKhZCDZBA4pyKzR8cdugs0kM7vGSGB0swdFWTt1V3oQVLhzLkHCwTvFS9NEeZAbTk7LXmQ9RhbdxJZAatoeweokiOMgLA2vPgDsXREY5ZBZAkZCMFTxqZA9nArIHFZBGCqrdu4WAP1nVE0G9ncOZCmsOGQyGNTyyI0qdAzwMEbB1mhaSz0kfGwZD",
                "instagramAccountId": "17841461958257523",
                "imageUrl": "https://pub-ad0474935e8d45af9db270f106d272ec.r2.dev/ai-ugc-test/ai-ugc-test/ai-ads-gen/image/png/generated_681369d941ab3.png",
                "primaryText": ["wedwedqwefqwef"],
                "headline": ["wedqwefqwe"],
                "description": ["wedwqwefq"],
                "landingUrl": "https://winninghunter.com",
                "callToAction": "SHOP_NOW",
                "adsets": ["120223396371790161"],
                "product_url": product_url,
                "ad_count": str(ad_count)
            }
            
            # Send request to API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://app.winninghunter.com/api/employee/create/imagead",
                    data=data,
                    files=files
                )
                
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"API request failed: {response.text}"
                )
                
            return response.json()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create ad images: {str(e)}")
            
        finally:
            # Close file objects
            for file in files.values():
                try:
                    file.close()
                except Exception as e:
                    print(f"Error closing file: {e}")
                    
            # Clean up temporary files
            for filepath in temp_filepaths:
                try:
                    if os.path.exists(filepath):
                        os.unlink(filepath)
                except Exception as e:
                    print(f"Failed to delete temp file {filepath}: {e}")


