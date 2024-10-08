import logging
import subprocess
import uuid
import boto3
import os
import json
import sys
import time

from botocore.exceptions import ClientError, DataNotFoundError

s3 = boto3.client('s3')
rek = boto3.client('rekognition')
sqs = boto3.client('sqs')
event = boto3.client('events')

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
    # dump event from queue, current parse for rekognition
    logger.info("Event: {}".format(json.dumps(event)))

    # fetch message from sqs
    for record in event['Records']:
        sqsResponse = json.loads(record['body'])
        rekMessage = json.loads(sqsResponse['Message'])

        logger.info('startJobId: {}, status: {}'.format(rekMessage['JobId'], rekMessage['Status']))
        logger.info('receive message from sqsUrl: {} as follows {}'.format(os.environ.get('QUEUE_URL'), json.dumps(sqsResponse)))
        
        # message validation
        if 'Message' not in sqsResponse:
            logger.error('JobId not found in message')
            return

        sqs.delete_message(QueueUrl=os.environ.get('QUEUE_URL'), ReceiptHandle=record['receiptHandle'])

        # download iframe from processed s3 bucket
        s3Object = rekMessage['Video']['S3ObjectName']
        s3Bucket = rekMessage['Video']['S3Bucket']
        iframePath = '/tmp/' + s3Object
        s3.download_file(s3Bucket, s3Object, iframePath)
        logger.info("Download I-Frames {} from S3 {}".format(s3Object, s3Bucket))

        # get shot info from reko result
        GetSegmentDetectionResults(rekMessage['JobId'], s3Object, s3Bucket, iframePath)

        # delete local file
        os.remove(iframePath)
        logger.info("Delete local file {}".format(iframePath))

def GetSegmentDetectionResults(jobId, s3Object, s3Bucket, iframePath, maxRetry=10, retryInterval=5, maxResults=10, nextToken=None):
    paginationToken = ""
    finished = False
    firstTime = True
    # slicedFilelist = []

    while finished == False:
        response = rek.get_segment_detection(
            JobId=jobId, MaxResults=maxResults, NextToken=paginationToken
        )
        logger.info('rekognition response: {}'.format(json.dumps(response)))
        """
        Sample response:
        {
            "JobStatus": "SUCCEEDED",
            "VideoMetadata": [
                {
                    "Codec": "h264",
                    "DurationMillis": 53428,
                    "Format": "QuickTime / MOV",
                    "FrameRate": 23.976024627685547,
                    "FrameHeight": 720,
                    "FrameWidth": 1280,
                    "ColorRange": "LIMITED"
                }
            ],
            "AudioMetadata": [
                {
                    "Codec": "aac",
                    "DurationMillis": 53440,
                    "SampleRate": 48000,
                    "NumberOfChannels": 2
                }
            ],
            "Segments": [
                {
                    "Type": "TECHNICAL_CUE",
                    "StartTimestampMillis": 0,
                    "EndTimestampMillis": 53386,
                    "DurationMillis": 53386,
                    "StartTimecodeSMPTE": "00:00:00:00",
                    "EndTimecodeSMPTE": "00:00:53:08",
                    "DurationSMPTE": "00:00:53:08",
                    "TechnicalCueSegment": {
                        "Type": "Content",
                        "Confidence": 100
                    },
                    "StartFrameNumber": 0,
                    "EndFrameNumber": 1280,
                    "DurationFrames": 1280
                },
                {
                    "Type": "SHOT",
                    "StartTimestampMillis": 0,
                    "EndTimestampMillis": 53386,
                    "DurationMillis": 53386,
                    "StartTimecodeSMPTE": "00:00:00:00",
                    "EndTimecodeSMPTE": "00:00:53:08",
                    "DurationSMPTE": "00:00:53:08",
                    "ShotSegment": {
                        "Index": 0,
                        "Confidence": 100
                    },
                    "StartFrameNumber": 0,
                    "EndFrameNumber": 1280,
                    "DurationFrames": 1280
                }
            ],
            "SelectedSegmentTypes": [
                {
                    "Type": "SHOT",
                    "ModelVersion": "2.0"
                },
                {
                    "Type": "TECHNICAL_CUE",
                    "ModelVersion": "2.0"
                }
            ],
            "JobId": "da9f552b1ce0feae3a01c36b4a7d21e49cb94e97f3c6ea8f14857047eefbcb65",
            "Video": {
                "S3Object": {
                    "Bucket": "kadastack-processed-video",
                    "Name": "clip_sample-01-iframe-output.mp4"
                }
            },
            "ResponseMetadata": {
                "RequestId": "cfc9ddd7-7766-42ef-8e94-23d83b974337",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "cfc9ddd7-7766-42ef-8e94-23d83b974337",
                    "content-type": "application/x-amz-json-1.1",
                    "content-length": "1217",
                    "date": "Tue, 20 Aug 2024 14:49:52 GMT"
                },
                "RetryAttempts": 0
            }
        }
TECHNICAL_CUE:
- Represents technical aspects of the video.
- Types include: Black Frames, Color Bars, End Credits, Opening Credits, Studio Logo, Slate, Content.
- Useful for identifying structural elements of the video.
- Often used in broadcast and professional video production workflows.

SHOT:
- Represents a continuous sequence of frames without a camera cut.
- Indicates scene changes or transitions in the video.
- Useful for understanding the visual structure and pacing of the video.
- Often used in video editing and content analysis.

For extracting a 3-5 minute video from a longer one based on video understanding, the SHOT segment type is generally more suitable due to considerations such as:

- Content-based segmentation: SHOT detection is more closely aligned with the actual content and narrative structure of the video. It identifies where the camera angle or scene changes, which often correlates with changes in the video's subject matter or focus.
- Semantic understanding: Shots often represent distinct semantic units in the video, making them more useful for understanding and summarizing the content.
- Granularity: Shots provide a finer level of granularity compared to most TECHNICAL_CUEs, allowing for more precise selection of important parts of the video.
- Narrative flow: By using shot boundaries, you're more likely to maintain a coherent narrative flow in your extracted video, as these boundaries often align with natural break points in the story or content.
        """
        if firstTime == True:
            print(f"Status\n------\n{response['JobStatus']}")
            # print("\nRequested Types\n---------------")
            # for selectedSegmentType in response['SelectedSegmentTypes']:
            #     print(f"\tType: {selectedSegmentType['Type']}")
            #     print(f"\t\tModel Version: {selectedSegmentType['ModelVersion']}")

            # print()
            print("\nAudio metadata\n--------------")
            # for audioMetadata in response['AudioMetadata']:
            #     print(f"\tCodec: {audioMetadata['Codec']}")
            #     print(f"\tDuration: {audioMetadata['DurationMillis']}")
            #     print(f"\tNumber of Channels: {audioMetadata['NumberOfChannels']}")
            #     print(f"\tSample rate: {audioMetadata['SampleRate']}")
            # print()
            print("\nVideo metadata\n--------------")
            # for videoMetadata in response["VideoMetadata"]:
            #     print(f"\tCodec: {videoMetadata['Codec']}")
            #     # print(f"\tColor Range: {videoMetadata['ColorRange']}")
            #     print(f"\tDuration: {videoMetadata['DurationMillis']}")
            #     print(f"\tFormat: {videoMetadata['Format']}")
            #     print(f"\tFrame rate: {videoMetadata['FrameRate']}")
            #     print(f"\tFrameHeight: {videoMetadata['FrameHeight']}")
            #     print(f"\tFrameWidth: {videoMetadata['FrameWidth']}")
            #     print("\nSegments\n--------")
            firstTime = False

        segments_meta = []
        for segment in response['Segments']:
            # print(f"\tDuration (milliseconds): {segment['DurationMillis']}")
            # print(f"\tStart Timestamp (milliseconds): {segment['StartTimestampMillis']}")
            # print(f"\tEnd Timestamp (milliseconds): {segment['EndTimestampMillis']}")
            
            # print(f"\tStart timecode: {segment['StartTimecodeSMPTE']}")
            # print(f"\tEnd timecode: {segment['EndTimecodeSMPTE']}")
            # print(f"\tDuration timecode: {segment['DurationSMPTE']}")

            # print(f"\tStart frame number {segment['StartFrameNumber']}")
            # print(f"\tEnd frame number: {segment['EndFrameNumber']}")
            # print(f"\tDuration frames: {segment['DurationFrames']}")

            """
            # generate random video clips from iframe video
            # ffmpeg -ss 00:01:00 -t 00:00:10 -i keyoutput.mp4 -vcodec copy -acodec copy output1.mp4
            RANDOM_VIDEO_FILE = str(uuid.uuid1()) + '-sliced-output.mp4'
            LOCAL_SLICED_VIDEO_FILE = '/tmp/' + RANDOM_VIDEO_FILE

            # archive sliced video to seperate folder with same iframe prefix
            REMOTE_SLICED_VIDEO_FILE = s3Object.split('.')[0] + '/' + RANDOM_VIDEO_FILE
            logger.info('REMOTE_SLICED_VIDEO_FILE is {}'.format(REMOTE_SLICED_VIDEO_FILE))

            CMD = ['ffmpeg', '-ss', segment['StartTimecodeSMPTE'].rsplit(':', 1)[0], '-t', segment['DurationSMPTE'].rsplit(':', 1)[0], '-i', iframePath, '-vcodec copy -acodec copy ', LOCAL_SLICED_VIDEO_FILE]
            SHELL_CMD = ' '.join(CMD)
            try:
                # out_bytes = subprocess.check_output(['./ffmpeg', '-y', '-i', LOCAL_VIDEO_FILE, '-strict', '-2', '-qscale', '0', '-intra', LOCAL_SLICED_VIDEO_FILE])
                out_bytes = subprocess.check_output(SHELL_CMD, shell=True)
                # Upload the transformed I-Frames to S3
                upload_file(LOCAL_SLICED_VIDEO_FILE, s3Bucket, REMOTE_SLICED_VIDEO_FILE)
                logger.info("Uploaded sliced I-Frames {} to S3".format(REMOTE_SLICED_VIDEO_FILE))

                # delete local file
                os.remove(LOCAL_SLICED_VIDEO_FILE)
                slicedFilelist.append(REMOTE_SLICED_VIDEO_FILE)
                logger.info('slicedFilelist is {}'.format(slicedFilelist))

            except subprocess.CalledProcessError as e:
                logger.error("Error: {}, return code {}".format(e.output.decode('utf-8'), e.returncode))
            """
            if segment['Type'] == 'SHOT':
                segment_info = {
                    'startTimecodeSMPTE': segment['StartTimecodeSMPTE'].rsplit(':', 1)[0],
                    'durationSMPTE': segment['DurationSMPTE'].rsplit(':', 1)[0],
                    'startTimestampMillis': segment['StartTimestampMillis'],
                    'endTimestampMillis': segment['EndTimestampMillis'],
                    'durationMillis': segment['DurationMillis']
                }
                segments_meta.append(segment_info)

        if "NextToken" in response:
            paginationToken = response["NextToken"]
            logger.info("Enter to next round processing, NextToken: {}".format(paginationToken))
        else:
            finished = True
            logger.info("All event been processed, update to dynamoDB")

            # TBD, generate a list of segments and using ffmpeg to cancatenate them
            # ffmpeg -f concat -safe 0 -i segments.txt -c copy output.mp4
            # ffmpeg -i segments.txt -c copy output.mp4

        # RANDOM_VIDEO_FILE = str(uuid.uuid1()) + '-sliced-output.mp4'
        # REMOTE_SLICED_VIDEO_FILE = s3Object.split('.')[0] + '/' + RANDOM_VIDEO_FILE
        # slicedFilelist.append(REMOTE_SLICED_VIDEO_FILE)
        # logger.info('slicedFilelist is as follows {}'.format(slicedFilelist))

        detail = {
            'jobId': jobId,
            # iframe video path
            's3Object': s3Object,
            's3Bucket': s3Bucket,
            'segmentsMeta': segments_meta
        }

        eventEntries = {
            'Time': time.time(),
            'Source': 'custom',
            'EventBusName': os.environ.get('EVENT_BUS_NAME'),
            'DetailType': 'videoShotsAndGif',
            'Detail': json.dumps(detail)
        }
        logger.info('eventEntries: {}'.format(json.dumps(eventEntries)))

        # put events to eventbridge
        event.put_events(Entries=[eventEntries])

        attemptCount = 0
        MAX_ATTEMPT = 3
        while (attemptCount < int(MAX_ATTEMPT)):
            ret = event.put_events(Entries=[eventEntries])
            # check ErrorCode or ErrorMessage for possible failure and retry
            try:
                if ret['FailedEntryCount'] == 0:
                    logger.info('put events result as follows\n %s' % json.dumps(ret, indent=4))
                    break
            except:
                logger.info('put events failed, retry after %s seconds' % retryInterval)
                time.sleep(retryInterval)
            attemptCount += 1

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
