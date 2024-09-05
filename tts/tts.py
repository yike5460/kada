import boto3
import os
import re
import logging
import argparse
from botocore.exceptions import BotoCoreError, ClientError
from pydub import AudioSegment
from tqdm import tqdm

# Configure logger
logger = logging.getLogger(__name__)

def setup_logging(debug=False):
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    if not debug:
        logging.getLogger().handlers = []  # Remove all handlers

def parse_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    subtitle_pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.+(?:\n.+)*))\n\n', re.MULTILINE)
    return subtitle_pattern.findall(content)

def parse_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    subtitles = []
    for i, line in enumerate(lines):
        # Assume each line is a separate subtitle with a default duration of 5 seconds
        start_time = f"00:00:{i*5:02d},000"
        end_time = f"00:00:{(i+1)*5:02d},000"
        subtitles.append((str(i+1), start_time, end_time, line.strip()))
    return subtitles

def time_to_ms(time_str):
    h, m, s = time_str.split(':')
    s, ms = s.split(',')
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)

def synthesize_speech(polly_client, text, voice_id):
    try:
        response = polly_client.synthesize_speech(
            Engine='generative',
            Text=text.strip(),
            OutputFormat='mp3',
            VoiceId=voice_id
        )
        if "AudioStream" in response:
            return response["AudioStream"].read()
    except (BotoCoreError, ClientError) as error:
        logger.error(f"Error synthesizing speech for text: {text}\nError: {error}")
    return None

def convert_text_to_speech(subtitle_file, voice_id, debug=False):
    setup_logging(debug)
    polly_client = boto3.client('polly')

    if subtitle_file.endswith('.srt'):
        subtitles = parse_srt(subtitle_file)
    elif subtitle_file.endswith('.txt'):
        subtitles = parse_txt(subtitle_file)
    else:
        raise ValueError("Unsupported file format. Please use .srt or .txt files.")

    logger.debug(f"Parsed {len(subtitles)} subtitles")

    full_audio = AudioSegment.silent(duration=0)
    last_end_time = 0

    logger.debug(f"Total subtitles: {len(subtitles)}")

    for _, (_, start, end, text) in tqdm(enumerate(subtitles), total=len(subtitles), desc="Processing subtitles"):
        start_ms = time_to_ms(start)
        end_ms = time_to_ms(end)

        logger.debug(f"Start: {start}, End: {end}")
        logger.debug(f"Text: {text}")

        if start_ms > last_end_time:
            silence_duration = start_ms - last_end_time
            full_audio += AudioSegment.silent(duration=silence_duration)
            logger.debug(f"Added silence: {silence_duration}ms")

        audio_data = synthesize_speech(polly_client, text, voice_id)
        if audio_data:
            temp_file = f"temp_{_}.mp3"
            with open(temp_file, 'wb') as file:
                file.write(audio_data)
            
            segment = AudioSegment.from_mp3(temp_file)
            segment_duration = min(len(segment), end_ms - start_ms)
            full_audio += segment[:segment_duration]
            last_end_time = start_ms + segment_duration
            logger.debug(f"Added audio segment: {segment_duration}ms")

            # Clean up temporary file immediately after use
            os.remove(temp_file)
        else:
            logger.warning(f"Could not synthesize audio for text: {text}")

        logger.debug(f"Current audio length: {len(full_audio)}ms")
        logger.debug("---")

    output_file = os.path.splitext(subtitle_file)[0] + '_synced.mp3'
    full_audio.export(output_file, format="mp3")
    logger.info(f"Synchronized speech saved to {output_file}")
    logger.debug(f"Final audio length: {len(full_audio)}ms")

def print_usage_instructions():
    print("Usage Instructions:")
    print("1. Install the required dependencies:")
    print("   pip install -r requirements.txt")
    print("2. Set up your AWS credentials (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)")
    print("3. Run the script with the following command:")
    print("   python tts.py <path_to_subtitle_file> <voice_id> [--debug]")
    print("   Example: python tts.py subtitles.srt Joanna")
    print("   Supported subtitle formats: .srt, .txt")
    # official documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/polly/client/synthesize_speech.html
    print("4. Available voice IDs can be found in the Amazon Polly documentation.")
    # since we are using the generative-latest engine, we are limited to Matthew and Ruth voices
    print("   - Matthew (US English, Male)")
    print("   - Ruth (US English, Female)")
    print("5. The output will be saved as '<input_file_name>_synced.mp3' in the same directory.")
    print("6. Use the --debug flag to enable detailed logging.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert subtitle file to synchronized speech using Amazon Polly")
    parser.add_argument("subtitle_file", nargs='?', help="Path to the subtitle file (.srt or .txt)")
    parser.add_argument("voice_id", nargs='?', help="Amazon Polly voice ID to use")
    parser.add_argument("--help-usage", action="store_true", help="Show usage instructions")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.help_usage:
        print_usage_instructions()
    elif args.subtitle_file and args.voice_id:
        convert_text_to_speech(args.subtitle_file, args.voice_id, args.debug)
    else:
        print("Error: Missing required arguments. Use --help-usage for instructions.")
        parser.print_help()