from __future__ import print_function
import json
import boto3
import logging
import time
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

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

        ec2 = boto3.resource('ec2')

        if eventname == 'CreateVolume':
            ids.append(detail['responseElements']['volumeId'])
            logger.info(ids)

        elif eventname == 'RunInstances':
            items = detail['responseElements']['instancesSet']['items']
            for item in items:
                ids.append(item['instanceId'])
            logger.info(ids)
            logger.info('number of instances: ' + str(len(ids)))

            base = ec2.instances.filter(InstanceIds=ids)

            #loop through the instances
            for instance in base:
                for vol in instance.volumes.all():
                    ids.append(vol.id)
                for eni in instance.network_interfaces:
                    ids.append(eni.id)

        elif eventname == 'CreateImage':
            ids.append(detail['responseElements']['imageId'])
            logger.info(ids)
        elif eventname == 'CreateSecurityGroup':
            ids.append(detail['responseElements']['groupId'])
            logger.info(ids)
        elif eventname == 'AllocateAddress':
            ids.append(detail['responseElements']['allocationId'])
            logger.info(ids)
        elif eventname == 'CreateSnapshot':
            ids.append(detail['responseElements']['snapshotId'])
            logger.info(ids)
        elif eventname == 'CreateLoadBalancer':
            if "loadBalancers" in detail['responseElements']:
                elbv2 = boto3.client('elbv2')
                dns = (detail['responseElements']['loadBalancers'][0]['loadBalancerArn'])
                elbv2.add_tags(ResourceArns=[dns], Tags=[{'Key': 'created_by_auto', 'Value': user}])
            else:
                elb = boto3.client('elb')
                dns = (detail['requestParameters']['loadBalancerName'])
                elb.add_tags(LoadBalancerNames=[dns], Tags=[{'Key': 'created_by_auto', 'Value': user}])
        else:
            logger.warning('Not supported action')
        if ids:
            for resourceid in ids:
                print('Tagging resource ' + resourceid)
            ec2.create_tags(Resources=ids, Tags=[{'Key': 'created_by_auto', 'Value': user}])

        logger.info(' Remaining time (ms): ' + str(context.get_remaining_time_in_millis()) + '\n')
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return False
