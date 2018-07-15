from __future__ import print_function
import json
import boto3
import logging
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    #logger.info('Event: ' + str(event))
    #print('Received event: ' + json.dumps(event, indent=2))

    ids = []

    try:
        region = event['region']
        detail = event['detail']
        eventname = detail['eventName']
        print("eventname is " +eventname)
        arn = detail['userIdentity']['arn']
        principal = detail['userIdentity']['principalId']
        userType = detail['userIdentity']['type']

        if userType == 'IAMUser':
            user = detail['userIdentity']['userName']

        else:
            user = principal.split(':')[1]


        logger.info('principalId: ' + str(principal))
        logger.info('region: ' + str(region))
        logger.info('eventName: ' + str(eventname))
        logger.info('detail: ' + str(detail))

        if not detail['responseElements']:
            logger.warning('Not responseElements found')
            if detail['errorCode']:
                logger.error('errorCode: ' + detail['errorCode'])
            if detail['errorMessage']:
                logger.error('errorMessage: ' + detail['errorMessage'])
            return False

        if eventname == 'CreateFunction20150331':
            arn = (detail['responseElements']['functionArn'])
            ld = boto3.client('lambda')
            ld.tag_resource(Resource=arn,Tags={'created_by_auto': user})
        elif eventname == 'CreateQueue':
            url = (detail['responseElements']['queueUrl'])
            sqs = boto3.client('sqs')
            sqs.tag_queue(QueueUrl=url,Tags={'created_by_auto': user})
        elif eventname == 'CreateBucket':
            id = (detail['requestParameters']['bucketName'])
            s3 = boto3.client('s3')
            s3.put_bucket_tagging(Bucket=resourceid, Tagging={'TagSet':[{'Key': 'created_by_auto', 'Value': user}]})
        elif eventname == 'CreateHostedZone':
            id = (detail['responseElements']['hostedZone']['id']).split("/")[2]
            print (id)
            route = boto3.client('route53')
            route.change_tags_for_resource(ResourceType='hostedzone',ResourceId=id,AddTags=[{'Key': 'created_by_auto', 'Value': user}])
        elif eventname == 'CreateHealthCheck':
            id = (detail['responseElements']['healthcheck']['id']).split("/")[2]
            print (id)
            route = boto3.client('route53')
            route.change_tags_for_resource(ResourceType='healthcheck',ResourceId=id,AddTags=[{'Key': 'created_by_auto', 'Value': user}])
        else:
            print ('nothing')
        logger.info(' Remaining time (ms): ' + str(context.get_remaining_time_in_millis()) + '\n')
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return False
