from __future__ import print_function
import hokuto

def lambda_handler(event, context):
    ret = hokuto.get_program_hokuto()
    with open('/tmp/hokuto.json', 'w') as f:
        f.write(ret) #
    #print(ret)
    import boto3
    from boto3.s3.transfer import S3Transfer
    s3client = boto3.client('s3')
    transfer = S3Transfer(s3client)
    transfer.upload_file('/tmp/hokuto.json',
                         'f7590088-74d7-418f-9f82-2fae8f371f63',
                         'hokuto.json',
                         extra_args={'ContentType': "application/json", 'ACL': 'public-read'})

if __name__ == '__main__':
    lambda_handler(None, None)

