from __future__ import print_function
import hokuto_27

def lambda_handler(event, context):
    ret = hokuto_27.get_program_hokuto()
    with open('/tmp/hokuto.json', 'w') as f:
        f.write(ret) #
    #print(ret)
    import boto3
    from boto3.s3.transfer import S3Transfer
    s3client = boto3.client('s3')
    transfer = S3Transfer(s3client)
    transfer.upload_file('/tmp/hokuto.json',
                         'b-sw.co',
                         'hokuto/hokuto.json',
                         extra_args={'ContentType': "application/json", 'ACL': 'public-read'})

if __name__ == '__main__':
    lambda_handler(None, None)

