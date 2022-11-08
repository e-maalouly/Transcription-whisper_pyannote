# Transcription

This script is for fixing two problems with the output of the [Whisper](https://github.com/openai/whisper) model:

1. Incorrect timestamps in the output.

2. Output stuck in a loop due to long segments of silence in the audio.

For fixing the first issue, I am using a slightly modified version of [stable-whisper](https://github.com/jianfch/stable-ts) by [jianfch](https://github.com/jianfch).

For the second issue, I use [pyannote audio](https://github.com/pyannote/pyannote-audio) to obtain non-silent audio segments, and feed those segments one after another into Whisper for transcription.

## Requirements

1. install [Whisper](https://github.com/openai/whisper#setup)

2. install [pyannote audio](https://github.com/pyannote/pyannote-audio#Installation)

3. clone this repository

### obtain Hugging Face token for pyannote audio:

1. Go to [VAD](https://huggingface.co/pyannote/voice-activity-detection) and accept user conditions. (You will have to create a Hugging Face account if you don't already have one)

2. Go to [tokens](https://huggingface.co/settings/tokens) and generate an access token.

3. Copy the generated token to a text file and name the text file "HuggingFaceToken.txt", and place the text file in the main folder of this repository.

## Usage

Place audio files(.wav or .mp3) or video files(.mp4) in the folder named "to_process". The script will batch process all files contained in the foler.

run the file "transcription.py" to obtain transcriptions for all the files in the folder "to_process".

Example commands for "transcription.py":

```
python transcription.py -l ja -v -srt
```
Transcribe files in Japanese and write a subtitle file with the timestamps and show the transcriptions while processing.

```
python transcription.py -l ja -task translate -txt -srt
```
Translate files from Japanese to English and write the translations in a text and a subtitle file with the timestamps.

```
python transcription.py -h
```
For a full list of commands.

