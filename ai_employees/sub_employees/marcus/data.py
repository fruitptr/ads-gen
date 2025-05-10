from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
from zoneinfo import ZoneInfo
import base64
import requests
from io import BytesIO
import os
from openai import OpenAI

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
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = requests.get(self.product_image_url)
            if response.status_code != 200:
                print(f"Failed to download image: {response.status_code}")
                raise Exception("Failed to download image")
            print("Image downloaded successfully.")
            
            # Create output directory if it doesn't exist
            output_dir = "generated_ads"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the downloaded image temporarily to ensure proper format
            temp_image_path = os.path.join(output_dir, "temp_source_image.png")
            with open(temp_image_path, "wb") as f:
                f.write(response.content)
            print(f"Saved temporary image to {temp_image_path}")
            
            # Generate ads based on ads_per_day
            for i in range(int(self.ads_per_day)):
                try:
                    # Basic prompt for the ad
                    prompt = f"Create a professional advertisement for this product. {self.ad_guidance}"
                    
                    # Call OpenAI API with the file opened properly
                    print("Calling OpenAI API...")
                    with open(temp_image_path, "rb") as image_file:
                        result = client.images.edit(
                            model="gpt-image-1",
                            image=image_file,
                            prompt=prompt
                        )
                    print("Result: ", result)
                    
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
                    
                except Exception as e:
                    print(f"Error generating ad {i+1}: {str(e)}")
            
            # Clean up the temporary file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                
            print(f"Ad generation complete. Generated {self.ads_per_day} ads.")
        except Exception as e:
            print("Error in execute: ", e)
