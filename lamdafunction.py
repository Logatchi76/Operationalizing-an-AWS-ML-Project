import base64
import logging
import json
import boto3

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

print('Loading Lambda function')

# Create SageMaker runtime client
runtime = boto3.Session().client('sagemaker-runtime')

# Update the endpoint name to match your actual endpoint
endpoint_Name = 'pytorch-inference-2024-10-28-15-14-59-651'

def lambda_handler(event, context):
    """
    Lambda handler function to invoke SageMaker endpoint
    """

    print('Context:::', context)
    print('EventType::', type(event))

    # The event should contain the necessary data for prediction
    bs = event

    try:
        # Call the SageMaker endpoint
        response = runtime.invoke_endpoint(
            EndpointName=endpoint_Name,
            ContentType="application/json",
            Accept='application/json',
            Body=json.dumps(bs)  # Ensure the body is a JSON formatted string
        )
        
        # Parse the result returned by the endpoint
        result = response['Body'].read().decode('utf-8')
        sss = json.loads(result)
        
        # Return the result as a response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*'},
            'type-result': str(type(result)),
            'Content-Type-In': str(context),
            'body': json.dumps(sss)
        }
    
    except Exception as e:
        logger.error(f"Error invoking endpoint: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
