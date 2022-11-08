import os
from os import walk
import argparse
from typing import Iterator, TextIO
from pydub import AudioSegment
from pyannote.audio import Pipeline
import whisper
from stable_whisper import modify_model, results_to_sentence


def srt_format_timestamp(seconds: float):

    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    return (f"{hours}:") + f"{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def write_srt(transcript: Iterator[dict], file: TextIO):

    count = 0
    for segment in transcript:
        count +=1
        print(
            f"{count}\n"
            f"{srt_format_timestamp(segment['start'])} --> {srt_format_timestamp(segment['end'])}\n"
            f"{segment['text'].replace('-->', '->').strip()}\n",
            file=file,
            flush=True,
        )  

def write_txt(transcript: Iterator[dict], file: TextIO):

    for segment in transcript:
        print(
            f"{segment['text'].replace('-->', '->').strip()}\n",
            file=file,
            flush=True,
        )  

def get_file_list(directory):

    files = []
    dir_path = directory
    for (dir, dir_names, file_name) in walk(dir_path):
        for file in file_name:
            files.append(dir + '/' + file)
    
    return files

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help = "The directory containing all the files to be processed", default = "./to_process")
    parser.add_argument("-t", "--task", choices = ["transcribe", "translate"], help = "Choose a task to perform", default = "transcribe")
    parser.add_argument("-l", "--language", help = "The original language of the file", default = "ja")
    parser.add_argument("-s", "--silence", type = int, help = "Specify the threshold for treating the segment as silence", default = "2000")
    parser.add_argument("-v", "--verbose", help = "Shows transctiption while processing", default = False, action="store_true")
    parser.add_argument("-txt", "--text", help = "Create text file of the transcription", default = False, action="store_true")
    parser.add_argument("-srt", "--subtitles", help = "Create srt subtitle file with timings", default = False, action="store_true")
    parser.add_argument("-tmp", "--temperature", type=float, help="temperature to use for sampling", default=0)
    parser.add_argument("-bs", "--beam_size", type = int, help = "number of beams in beam search, only applicable when temperature is zero", default = 5)
    parser.add_argument("-bo", "--best_of", type = int, help = "number of candidates when sampling with non-zero temperature", default = 5)
    args = parser.parse_args()

    print("Task to be carried out: ", args.task)
    print("Original language of files: ", args.language)
    print("The threshold for considering the segment as silence: ", args.silence)

    model = whisper.load_model("large")
    modify_model(model)

    # obtain a list of files to be processed
    files = get_file_list(args.directory)

    for file in files:
        print('processing', file)

        name = os.path.splitext(file)[0]
        ext = os.path.splitext(file)[1]

        if ext.casefold() in ['.mp3', '.wav']:
            remove_after_processing = False
        elif ext.casefold() in ['.mp4']:
            print('Extracting audio file from video')
            os.system('ffmpeg -i {} -acodec pcm_s16le -ar 16000 {}.wav'.format(file, name))
            file = name + '.wav'
            remove_after_processing = True
        else:
            continue

        HuggingFaceToken = open("HuggingFaceToken.txt").read()
        pipeline = Pipeline.from_pretrained("pyannote/voice-activity-detection", use_auth_token = HuggingFaceToken)

        # obtain voice activity segments
        wav = AudioSegment.from_wav(file)  
        vad_res = pipeline(file)
        timeline = vad_res.get_timeline().support()

        # initialization of variables
        current_prompt = ""
        full_transciption = []

        for seg in timeline:
            
            # segment timestamps
            t_start = (seg.start * 1000) - 300
            t_end = (seg.end * 1000) + 300

            if t_start < 0:
                t_start = 0

            # export to file
            audio_seg = wav[t_start:t_end]

            # check if silence threshold is appropriate
            if args.verbose:
                print("\nLoudness: ", audio_seg.max)

            # skip segment if audio is below silence threshold
            if audio_seg.max < args.silence:
                continue

            audio_seg.export('temp.wav', 
                        format='wav', parameters=['-sample_fmt', 's16', '-ar', '16000'])

            #transcribe or translate audio        
            result = model.transcribe(
                'temp.wav',
                task = args.task,
                language = args.language,
                prompt = current_prompt,
                condition_on_previous_text = True,
                temperature = args.temperature,
                beam_size = args.beam_size,
                best_of = args.best_of)
            
            try:
                segment_result = results_to_sentence(result)
            except:
                continue
            
            if segment_result:                        
                # obtain transcription and timestamps of each segment
                for seg in segment_result:    
                    current_prompt = seg['text']
                    start = seg['start'] + t_start / 1000
                    end = seg['end'] + t_start / 1000

                    if args.verbose:
                        print(start, "---->", end)
                        print(current_prompt)
                        print('-----------------------------------------------------------------------------')

                    # append results to full transcription
                    full_transciption.append({'text' : current_prompt, 'start' : start, 'end' : end})

        if args.task.casefold() in ['transcribe']:
            target_language = args.language
        else:
            target_language = "en"

        # write full transcription to text file
        if args.text:
            with open(name + f".{target_language}.txt", "w") as txt:
                write_txt(full_transciption, file = txt)
        
        # write full transcription to srt
        if args.subtitles:
            with open(name + f".{target_language}.srt", "w") as srt:
                write_srt(full_transciption, file=srt)
        
        # remove extracted audio file
        if remove_after_processing:
            os.remove(file)
            os.remove('temp.wav')
            remove_after_processing = False


if __name__ == '__main__':
    main()