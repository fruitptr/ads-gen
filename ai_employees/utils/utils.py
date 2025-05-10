import mysql.connector
from mysql.connector import Error
import boto3
from botocore.exceptions import ClientError
import os
import base64
import traceback

def connect_to_database():
    """Establish a connection to the MySQL database using credentials from .env file."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("APP_DB_HOST", "localhost"),
            database=os.getenv("APP_DB_NAME", "dropshipspy"),
            user=os.getenv("APP_DB_USER", "root"),
            password=os.getenv("APP_DB_PASSWORD", ""),
            port=os.getenv("APP_DB_PORT", "3306")
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None

def ensure_table_exists(connection):
    """Check if the employee_ai_ads_images table exists, create it if it doesn't."""
    if not connection:
        return False
    
    cursor = connection.cursor()
    try:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_name = %s
        """, (os.getenv("APP_DB_NAME", "dropshipspy"), "employee_ai_ads_images"))
        
        if cursor.fetchone()[0] == 0:
            # Table doesn't exist, create it
            cursor.execute("""
                CREATE TABLE employee_ai_ads_images (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    userid VARCHAR(255) NOT NULL,
                    image_url VARCHAR(255) NOT NULL,
                    is_evaluated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            print("Table employee_ai_ads_images created successfully")
        return True
    except Error as e:
        print(f"Error checking/creating table: {e}")
        return False
    finally:
        cursor.close()

def save_image_url_to_db(connection, userid, image_url):
    """Save the image URL to the database."""
    if not connection:
        return False
    
    cursor = connection.cursor()
    try:
        query = """
            INSERT INTO employee_ai_ads_images (userid, image_url, is_evaluated)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (userid, image_url, False))
        connection.commit()
        print(f"Image URL saved to database with ID: {cursor.lastrowid}")
        return True
    except Error as e:
        print(f"Error saving image URL to database: {e}")
        return False
    finally:
        cursor.close()

def close_connection(connection):
    """Close the database connection."""
    if connection and connection.is_connected():
        connection.close()
        print("MySQL connection closed")

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