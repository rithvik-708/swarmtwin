import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
import json
import os
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("SwarmTwin.AWS")

class AWSManager:
    """
    AWS Persistence Manager for SwarmTwin.
    Connects to Amazon S3 for disaster evidence frame persistence
    and Amazon DynamoDB for immutable incident audit trails.
    Includes robust local disk fallback when running in offline or test environments.
    """
    def __init__(
        self,
        region_name: Optional[str] = None,
        bucket_name: Optional[str] = None,
        table_name: Optional[str] = None,
        local_fallback_dir: str = "data/aws_local_store"
    ):
        self.region = region_name or os.getenv('AWS_REGION', 'us-east-1')
        self.bucket = bucket_name or os.getenv('S3_BUCKET_NAME') or os.getenv('S3_BUCKET', 'swarmtwin-evidence-frames')
        self.table_name = table_name or os.getenv('DYNAMO_TABLE_NAME') or os.getenv('DYNAMODB_TABLE', 'SwarmTwinIncidents')
        self.local_fallback_dir = local_fallback_dir
        os.makedirs(self.local_fallback_dir, exist_ok=True)

        self.s3_available = False
        self.dynamo_available = False
        self.s3 = None
        self.dynamodb = None
        self.table = None

        try:
            session = boto3.Session(region_name=self.region)
            creds = session.get_credentials()
            if creds and creds.access_key:
                self.s3 = session.client('s3')
                self.dynamodb = session.resource('dynamodb')
                self.table = self.dynamodb.Table(self.table_name)
                self.s3_available = True
                self.dynamo_available = True
                logger.info(f"AWS Cloud Persistence active: S3 ({self.bucket}) + DynamoDB ({self.table_name}) [{self.region}]")
            else:
                logger.info(f"AWS credentials not detected. Operating in Local Persistence Mode ({self.local_fallback_dir})")
        except Exception as e:
            logger.info(f"AWS clients running in Local Persistence Mode: {e}")

    def upload_frame(self, image_bytes: bytes, filename: str) -> str:
        """
        Uploads JPEG disaster evidence frame to Amazon S3 (if cloud credentials available)
        or persists locally in data/aws_local_store.
        Returns the S3 URL (or simulated public URL in local mode).
        """
        s3_url = f"https://{self.bucket}.s3.amazonaws.com/{filename}"
        
        # Save local copy for guaranteed offline persistence
        local_path = os.path.join(self.local_fallback_dir, filename)
        try:
            with open(local_path, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            logger.warning(f"Local frame cache failed: {e}")

        if self.s3_available and self.s3 is not None:
            try:
                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=filename,
                    Body=image_bytes,
                    ContentType='image/jpeg'
                )
                logger.info(f"Successfully uploaded evidence frame to S3: {s3_url}")
            except Exception as e:
                logger.warning(f"S3 cloud upload failed ({e}); local copy retained at {local_path}")

        return s3_url

    def save_incident(self, incident_id: str, final_status: str, trace: list) -> Dict[str, Any]:
        """
        Persists incident metadata and multi-step agent trace to Amazon DynamoDB
        (if cloud credentials available) and always saves local JSON record.
        """
        timestamp = int(time.time())
        item = {
            'IncidentId': incident_id,
            'FinalStatus': final_status,
            'TraceLog': json.dumps(trace),
            'Timestamp': timestamp
        }

        # Save local JSON record
        local_record = os.path.join(self.local_fallback_dir, f"{incident_id}.json")
        try:
            with open(local_record, "w") as f:
                json.dump(item, f, indent=2)
        except Exception as e:
            logger.warning(f"Local incident record save failed: {e}")

        if self.dynamo_available and self.table is not None:
            try:
                self.table.put_item(Item=item)
                logger.info(f"Successfully saved incident {incident_id} to DynamoDB table {self.table_name}")
            except Exception as e:
                logger.warning(f"DynamoDB cloud save failed ({e}); local audit trail retained at {local_record}")

        return item
