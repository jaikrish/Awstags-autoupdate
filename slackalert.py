import os, json, boto3
import urllib2
import time
def send_message_to_slack(text):
    post = {"text": "{0}".format(text)}
    try:
        json_data = json.dumps(post)
        req = urllib2.Request(" slack imcoming webhook url ",
                              data=json_data.encode('ascii'),
                              headers={'Content-Type': 'application/json'})
        resp = urllib2.urlopen(req)
    except Exception as em:
        print("EXCEPTION: " + str(em))
def print_table(lines, separate_head=True):
      """Prints a formatted table given a 2 dimensional array"""
      #Count the column width
      widths = []
      for line in lines:
          for i,size in enumerate([len(x) for x in line]):
              while i >= len(widths):
                  widths.append(0)
              if size > widths[i]:
                  widths[i] = size
      #Generate the format string to pad the columns
      print_string = ""
      for i,width in enumerate(widths):
          print_string += "{" + str(i) + ":" + str(width) + "} | "
      if (len(print_string) == 0):
          return
      print_string = print_string[:-3]
      table = []
      for i,line in enumerate(lines):
          table.append(print_string.format(*line))
          if (i == 0 and separate_head):
              table.append("-"*(sum(widths)+3*(len(widths)-1)))
      return(table)
def lambda_handler(event, context):
 regions = ["us-east-1","ap-south-1","ap-southeast-1"]
 result = dict()
 for region in regions:
        client = boto3.client('resourcegroupstaggingapi',region_name=region)
        s = client.get_resources(TagFilters=[{'Key': 'created_by_auto'}],ResourceTypeFilters=["ec2:image","ec2:snapshot","elasticloadbalancing:loadbalancer","ec2:security-group","s3"])
        resourcelist = s['ResourceTagMappingList']
        for res in resourcelist:
                arn = res['ResourceARN']
                tags = res['Tags']
                for tag in tags:
                        if tag['Key'] == 'created_by_auto':
                                owner =tag['Value']
                                if owner not in result:
                                        result[owner] = []
                                result[owner].append(arn)
 row = []
 row.append(("USER", "REGION", "SERVICE", "RESOURCE", "CREATIONDATE"))
 for keys,values in result.items():
        for value in values:
            region = value.split(":")[3]
            service = value.split(":")[2]
            resource_reference = value.split(":")[5]
            reso = value.split(":")[-1].split("/")[0]
            reso2 = value.split(":")[-1].split("/")[-1]
            if (service == "s3"):
                s3 = boto3.resource('s3')
                r = s3.Bucket(resource_reference).creation_date.strftime("%d/%m/%Y")
            elif (reso == "image"):
                ec2 = boto3.resource('ec2', region_name=region)
                r = ec2.Image(reso2).creation_date.split("T")[0]
            elif (reso == "snapshot"):
                ec2 = boto3.resource('ec2', region_name=region)
                r = ec2.Snapshot(reso2).start_time.strftime("%d/%m/%Y")
            elif (reso == "loadbalancer"):
                reso3 = value.split(":")[-1].split("/")[1]
                if (reso3 == "app" or reso3 == "net"):
                    lb2 = boto3.client('elbv2')
                    lb = lb2.describe_load_balancers(LoadBalancerArns=[value])
                    r = (lb['LoadBalancers'][0]['CreatedTime'].strftime("%d/%m/%Y"))
                else:
                    lb1 = boto3.client('elb')
                    lb = lb1.describe_load_balancers(LoadBalancerNames=[reso3])
                    r = (lb['LoadBalancerDescriptions'][0]['CreatedTime'].strftime("%d/%m/%Y"))
            elif (reso == "security-group"):
                r = " "
            else:
                r = " "
            row.append((keys, region, service, resource_reference, r))
 for region in regions:
        ld = boto3.client('lambda', region_name=region)
        d = []
        l = ld.list_functions()
        for fun in l['Functions']:
                d.append(fun['FunctionArn'])
        for dto in d:
                ltag = ld.list_tags(Resource=dto)
                if 'created_by_auto' in (ltag['Tags']):
                        ldate = (ld.get_function(FunctionName=dto))
                        region = dto.split(":")[3]
                        service = dto.split(":")[2]
                        resource_reference = dto.split(":")[6]
                        r = ((ldate['Configuration']['LastModified']).split("T")[0])
                        keys = (ldate['Tags']['created_by_auto'])
                        row.append((keys, region, service, resource_reference, r))
 for region in regions:
        sqs = boto3.client('sqs',  region_name=region)
        l = sqs.list_queues()
        if 'QueueUrls' in l:
                for urls in l['QueueUrls']:
                        a = sqs.list_queue_tags(QueueUrl=urls)
                        if 'Tags' in a:
                                if 'created_by_auto' in (a['Tags']):
                                        ct = sqs.get_queue_attributes(QueueUrl=urls,AttributeNames=['CreatedTimestamp'])
                                        service = "SQS"
                                        resource_reference = urls.split(":")[-1].split("/")[4]
                                        tm = float(ct['Attributes']['CreatedTimestamp'])
                                        r = time.strftime("%Y-%m-%d", time.gmtime(tm))
                                        keys = (a['Tags']['created_by_auto'])
                                        row.append((keys, region, service, resource_reference, r))
 result_table = (print_table(row))
 r = "```\n\n Tag Enforcement - Audit Report: %s \n \n" % (time.strftime("%Y-%m-%d %H:%M")) + "\n".join(result_table) + "```"
 send_message_to_slack(r)

