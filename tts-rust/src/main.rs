use aws_sdk_polly::Client;
use aws_sdk_polly::types::{Engine, OutputFormat, VoiceId};
use clap::Parser;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use anyhow::{Context, Result};

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

    for line in reader.lines() {
        let line = line?;
        line_count += 1;

        match line_count % 4 {
            0 => {
                // Empty line, process the subtitle
                if !subtitle.text.is_empty() {
                    process_subtitle(&client, &voice_id, &engine, &subtitle, &mut output_file).await?;
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
        process_subtitle(&client, &voice_id, &engine, &subtitle, &mut output_file).await?;
    }

    Ok(())
}

async fn process_subtitle(
    client: &Client,
    voice_id: &VoiceId,
    engine: &Engine,
    subtitle: &Subtitle,
    output_file: &mut File,
) -> Result<()> {
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

    // Add silence to sync with timestamp
    let start_time = parse_timestamp(&subtitle.start_time)?;
    let end_time = parse_timestamp(&subtitle.end_time)?;
    let duration = end_time - start_time;
    let silence_duration = (duration - audio_data.len() as f64 / 16000.0).max(0.0);
    if silence_duration > 0.0 {
        let silence_samples = (silence_duration * 16000.0) as usize;
        let silence = vec![0u8; silence_samples * 2];
        output_file.write_all(&silence).context("Failed to write silence")?;
    }

    Ok(())
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