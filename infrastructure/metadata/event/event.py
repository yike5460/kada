import logging
import subprocess
import uuid
import boto3
import os
import json
import sys
import time

from botocore.exceptions import ClientError

SIGNED_URL_EXPIRATION = 60 * 60 * 24 * 7

s3 = boto3.client('s3')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE'))

LAMBDA_TASK_ROOT = os.environ.get('LAMBDA_TASK_ROOT')
# ffmpeg_path = os.path.join(LAMBDA_TASK_ROOT, 'ffmpeg')

logger = logging.getLogger('boto3')
logger.setLevel(logging.INFO)

# add execution path to ffmpeg
os.environ['PATH'] = os.environ['PATH'] + ':' + os.environ['LAMBDA_TASK_ROOT']

# testing with command aws s3 rm s3://metadata-original-video/SampleVideo_1280x720_30mb.mp4 && aws s3 cp SampleVideo_1280x720_30mb.mp4 s3://metadata-original-video/
def lambda_handler(event, context):
    """

    :param event:
    :param context:
    """
    # dump event from queue, current parse for rekognition, sample event:
    # {'version': '0',
    # 'id': 'a4a6afa9-d9ea-4fe3-0128-6798ab53cd7e',
    # 'detail-type': 'videoShotsAndGif',
    # 'source': 'custom',
    # 'account': '705247044519',
    # 'time': '2024-08-20T14:49:53Z',
    # 'region': 'us-east-1',
    # 'resources': [],
    # 'detail': {
    #   'jobId': 'da9f552b1ce0feae3a01c36b4a7d21e49cb94e97f3c6ea8f14857047eefbcb65',
    #   's3Object': 'clip_sample-01-iframe-output.mp4',
    #   's3Bucket': 'kadastack-processed-video',
    #   'segmentsMeta': [
    #     {
    #       'startTimecodeSMPTE': '00:01:00',
    #       'durationSMPTE': '00:00:10',
    #       'startTimestampMillis': 60000,
    #       'endTimestampMillis': 70000,
    #       'durationMillis': 10000
    #     },
    #     ...
    #   ]
    # }}
    logger.info("raw event from EventBridge: {}".format(event))

    # parse event from eventbridge
    event_source = event['source']
    event_detail = event['detail']
    event_detail_type = event['detail-type']

    # generate random video clips from iframe video
    if event_detail_type == 'videoShotsAndGif' and event_source == 'custom':
        s3Object = event_detail['s3Object']
        s3Bucket = event_detail['s3Bucket']
        """
        The event detail is updated with schema below:
        segments_meta = []
        segment_info = {
            'startTimecodeSMPTE': segment['StartTimecodeSMPTE'].rsplit(':', 1)[0],
            'durationSMPTE': segment['DurationSMPTE'].rsplit(':', 1)[0],
            'startTimestampMillis': segment['StartTimestampMillis'],
            'endTimestampMillis': segment['EndTimestampMillis'],
            'durationMillis': segment['DurationMillis']
        }
        segments_meta.append(segment_info)
        detail = {
            'jobId': jobId,
            # iframe video path
            's3Object': s3Object,
            's3Bucket': s3Bucket,
            'segmentsMeta': segments_meta
        }
        """
        segments_meta = event_detail['segmentsMeta']
        signed_url = get_signed_url(SIGNED_URL_EXPIRATION, s3Bucket, s3Object)
        # double quote the singed url
        signed_url = '"' + signed_url + '"'
        logger.info("iframe video bucket: {}, key: {}, signed URL: {}".format(s3Bucket, s3Object, signed_url))

        for segment in segments_meta:
            RANDOM_VIDEO_FILE = str(uuid.uuid4()) + '-sliced-output.mp4'
            RANDOM_GIF_FILE = str(uuid.uuid4()) + '-sliced-output.gif'

            startTimecodeSMPTE = segment['startTimecodeSMPTE']
            durationSMPTE = segment['durationSMPTE']

            LOCAL_SLICED_VIDEO_FILE = '/tmp/' + RANDOM_VIDEO_FILE
            LOCAL_SLICED_GIF_FILE = '/tmp/' + RANDOM_GIF_FILE
            REMOTE_SLICED_VIDEO_FILE = s3Object.split('.')[0] + '/' + RANDOM_VIDEO_FILE
            REMOTE_SLICED_GIF_FILE = s3Object.split('.')[0] + '/' + RANDOM_GIF_FILE

            # slice video
            CMD = ['ffmpeg', '-ss', startTimecodeSMPTE, '-t', durationSMPTE, '-i', signed_url, '-vcodec copy -acodec copy ', LOCAL_SLICED_VIDEO_FILE]
            SHELL_CMD = ' '.join(CMD)
            try:
                subprocess.check_output(SHELL_CMD, shell=True)
                upload_file(LOCAL_SLICED_VIDEO_FILE, s3Bucket, REMOTE_SLICED_VIDEO_FILE)
                logger.info("Uploaded sliced I-Frames {} to S3".format(REMOTE_SLICED_VIDEO_FILE))
                os.remove(LOCAL_SLICED_VIDEO_FILE)
            except subprocess.CalledProcessError as e:
                logger.error("Error: {}, return code {}".format(e.output.decode('utf-8'), e.returncode))

            # generate gif from sliced video
            CMD = ['ffmpeg', '-loglevel error -ss', startTimecodeSMPTE, '-t', durationSMPTE, '-y -i', signed_url, '-vf "fps=10,scale=240:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0', LOCAL_SLICED_GIF_FILE]
            SHELL_CMD = ' '.join(CMD)
            try:
                subprocess.check_output(SHELL_CMD, shell=True)
                upload_file(LOCAL_SLICED_GIF_FILE, s3Bucket, REMOTE_SLICED_GIF_FILE)
                logger.info("Uploaded sliced GIF image {} to S3".format(REMOTE_SLICED_GIF_FILE))
                os.remove(LOCAL_SLICED_GIF_FILE)
            except subprocess.CalledProcessError as e:
                logger.error("Error: {}, return code {}".format(e.output.decode('utf-8'), e.returncode))

        # Update sliced video and GIF info to DynamoDB
        logger.info('DynamoDB key is {}'.format(s3Object.split('.')[0].rsplit('-')[0] + '.' + s3Object.split('.')[1]))
        
        sliced_video_list = [s3Object.split('.')[0] + '/' + segment['startTimecodeSMPTE'] + '-' + segment['durationSMPTE'] + '-sliced-output.mp4' for segment in segments_meta]
        sliced_gif_list = [s3Object.split('.')[0] + '/' + segment['startTimecodeSMPTE'] + '-' + segment['durationSMPTE'] + '-sliced-output.gif' for segment in segments_meta]
        try:
            table.update_item(
                Key={
                # Strip -iframe-output to restore original video name, 'SampleVideo_1280x720_30mb-iframe-output.mp4' to 'SampleVideo_1280x720_30mb.mp4'
                'id': s3Object.split('.')[0].rsplit('-')[0] + '.' + s3Object.split('.')[1]
            },
            UpdateExpression="set #slicedVideos = :slicedVideos, #slicedGifs = :slicedGifs, #s3Bucket = :s3Bucket",
            ExpressionAttributeNames={
                '#slicedVideos': 'slicedVideos',
                '#slicedGifs': 'slicedGifs',
                '#s3Bucket': 's3Bucket'
            },
            ExpressionAttributeValues={
                ':slicedVideos': sliced_video_list,
                ':slicedGifs': sliced_gif_list,
                ':s3Bucket': s3Bucket
            }
        )
            logger.info("Updated sliced video and GIF info to DynamoDB")
        except Exception as e:
            logger.error("Error: {}, return code {}".format(e.output.decode('utf-8'), e.returncode))
            logger.error("Failed to update sliced video and GIF info to DynamoDB")

def get_signed_url(expires_in, bucket, obj):
    """
    Generate a signed URL
    :param expires_in:  URL Expiration time in seconds
    :param bucket:
    :param obj:         S3 Key name
    :return:            Signed URL
    """
    s3_cli = boto3.client("s3")
    presigned_url = s3_cli.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': obj}, ExpiresIn=expires_in)
    return presigned_url

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    try:
        response = s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True
 
    