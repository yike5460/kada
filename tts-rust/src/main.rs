use aws_sdk_polly::Client;
use aws_sdk_polly::types::{Engine, OutputFormat, VoiceId};
use clap::Parser;
use std::fs::File;
use std::io::{BufRead, BufReader, Write, Seek, SeekFrom};
use anyhow::{Context, Result};
use mp3_duration;
use tempfile::NamedTempFile;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long)]
    input: String,
    #[arg(short, long)]
    output: String,
    #[arg(short, long)]
    voice: String,
    #[arg(short, long)]
    engine: String,
}

struct Subtitle {
    start_time: String,
    end_time: String,
    text: String,
}

// Usage: cargo run -- --input sample.srt --output output_synced.mp3 --voice Matthew --engine generative
#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    let config = aws_config::load_defaults(aws_config::BehaviorVersion::latest()).await;
    let client = Client::new(&config);

    let voice_id = VoiceId::from(args.voice.as_str());
    let engine = Engine::from(args.engine.as_str());

    let mut output_file = File::create(&args.output).context("Failed to create output file")?;
    let input_file = File::open(&args.input).context("Failed to open input file")?;
    let reader = BufReader::new(input_file);

    let mut subtitle = Subtitle {
        start_time: String::new(),
        end_time: String::new(),
        text: String::new(),
    };
    let mut line_count = 0;
    let mut current_time = 0.0;
    let mut temp_file = NamedTempFile::new().context("Failed to create temp file")?;
    let mut temp_writer = temp_file.reopen().context("Failed to open temp file for writing")?;

    for line in reader.lines() {
        let line = line?;
        line_count += 1;

        match line_count % 4 {
            0 => {
                // Empty line, process the subtitle
                if !subtitle.text.is_empty() {
                    process_subtitle(&client, &voice_id, &engine, &subtitle, &mut temp_writer, &mut current_time).await?;
                }
                subtitle.text.clear();
            }
            1 => {
                // Subtitle number, ignore
            }
            2 => {
                // Timestamp
                let times: Vec<&str> = line.split(" --> ").collect();
                if times.len() == 2 {
                    subtitle.start_time = times[0].to_string();
                    subtitle.end_time = times[1].to_string();
                }
            }
            3 => {
                // Subtitle text
                subtitle.text.push_str(&line);
            }
            _ => unreachable!(),
        }
    }

    // Process the last subtitle if any
    if !subtitle.text.is_empty() {
        process_subtitle(&client, &voice_id, &engine, &subtitle, &mut temp_writer, &mut current_time).await?;
    }

    // Copy the temp file to the output file
    temp_writer.seek(SeekFrom::Start(0))?;
    std::io::copy(&mut temp_writer, &mut output_file)
        .context("Failed to copy temp file to output file")?;

    Ok(())
}

async fn process_subtitle(
    client: &Client,
    voice_id: &VoiceId,
    engine: &Engine,
    subtitle: &Subtitle,
    output_file: &mut impl Write,
    current_time: &mut f64,
) -> Result<()> {
    let start_time = parse_timestamp(&subtitle.start_time)?;
    let end_time = parse_timestamp(&subtitle.end_time)?;

    // Add silence if needed before the current subtitle
    if *current_time < start_time {
        let silence_duration = start_time - *current_time;
        add_silence(output_file, silence_duration)?;
    }

    let resp = client
        .synthesize_speech()
        .output_format(OutputFormat::Mp3)
        .text(&subtitle.text)
        .voice_id(voice_id.clone())
        .engine(engine.clone())
        .send()
        .await
        .context("Failed to synthesize speech")?;

    let audio_data = resp.audio_stream.collect().await?.into_bytes();
    output_file.write_all(&audio_data).context("Failed to write audio data")?;

    // Get the duration of the synthesized audio
    let audio_duration = get_mp3_duration(&audio_data)?;

    // Update current_time
    *current_time = start_time + audio_duration;

    // Add silence if needed after the current subtitle
    if *current_time < end_time {
        let silence_duration = end_time - *current_time;
        add_silence(output_file, silence_duration)?;
        *current_time = end_time;
    }

    Ok(())
}

fn add_silence(output_file: &mut impl Write, duration: f64) -> Result<()> {
    // Create a silent MP3 frame
    let silent_frame = create_silent_mp3_frame(duration)?;
    output_file.write_all(&silent_frame).context("Failed to write silence")?;
    Ok(())
}

fn create_silent_mp3_frame(duration: f64) -> Result<Vec<u8>> {
    // This is a simplified version. For production use, consider using a proper MP3 encoding library.
    let frame_duration = 0.026; // Approximately 26ms per frame
    let num_frames = (duration / frame_duration).ceil() as usize;
    
    // A basic silent MP3 frame (44.1kHz, 128kbps, mono)
    let silent_frame = vec![
        0xFF, 0xFB, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ];

    let mut silent_audio = Vec::new();
    for _ in 0..num_frames {
        silent_audio.extend_from_slice(&silent_frame);
    }

    Ok(silent_audio)
}

fn get_mp3_duration(data: &[u8]) -> Result<f64> {
    let duration = mp3_duration::from_read(&mut std::io::Cursor::new(data))
        .context("Failed to get MP3 duration")?;
    Ok(duration.as_secs_f64())
}

fn parse_timestamp(timestamp: &str) -> Result<f64> {
    let parts: Vec<&str> = timestamp.split(':').collect();
    if parts.len() != 3 {
        anyhow::bail!("Invalid timestamp format");
    }
    let hours: f64 = parts[0].parse()?;
    let minutes: f64 = parts[1].parse()?;
    let seconds_parts: Vec<&str> = parts[2].split(',').collect();
    if seconds_parts.len() != 2 {
        anyhow::bail!("Invalid seconds format");
    }
    let seconds: f64 = seconds_parts[0].parse()?;
    let milliseconds: f64 = seconds_parts[1].parse()?;
    Ok(hours * 3600.0 + minutes * 60.0 + seconds + milliseconds / 1000.0)
}