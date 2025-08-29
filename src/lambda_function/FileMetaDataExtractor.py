import json
import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
processed_bucket = os.environ['PROCESSED_BUCKET']

def lambda_handler(event, context):
    # S3 이벤트에서 버킷 이름과 객체 키 추출
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    try:
        print(f"Processing file: {key} from bucket: {bucket}")
        
        # S3 객체 메타데이터 가져오기
        response = s3.head_object(Bucket=bucket, Key=key)
        
        # 메타데이터 추출
        file_size = response['ContentLength']
        file_type = response['ContentType']
        
        # 고유 file_id 생성
        file_id = key
        
        # 메타데이터 객체 생성
        metadata = {
            'file_id': file_id,
            'timestamp': datetime.now().isoformat(),
            'file_name': key,
            'file_size': file_size,
            'file_type': file_type,
            'status': 'COMPLETED',
            'processed_location': f"s3://{bucket}/{key}"
        }
        
        # DynamoDB에 메타데이터 저장
        table.put_item(Item=metadata)
        print(f"Metadata saved to DynamoDB: {metadata}")
        
        # S3에 메타데이터 JSON 파일 저장
        metadata_key = f"metadata/{key}.json"
        
        s3.put_object(
            Bucket=processed_bucket,
            Key=metadata_key,
            Body=json.dumps(metadata),
            ContentType='application/json'
        )
        print(f"Metadata saved to S3: s3://{processed_bucket}/{metadata_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Metadata extraction successful')
        }
    
    except Exception as e:
        print(f"Error processing file {key}: {str(e)}")
        error_metadata = {
            'file_id': key,
            'timestamp': datetime.now().isoformat(),
            'status': 'FAILED',
            'error_message': str(e)
        }
        
        # DynamoDB에 오류 상태 저장
        table.put_item(Item=error_metadata)
        
        # S3에 오류 정보 저장
        error_key = f"errors/{key}_error.json"
        s3.put_object(
            Bucket=processed_bucket,
            Key=error_key,
            Body=json.dumps(error_metadata),
            ContentType='application/json'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps('Error in metadata extraction')
        }
