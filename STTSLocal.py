import base64
import io
import json
import os
import subprocess
import time
import traceback
import wave
from threading import Thread
from typing import Union, Optional, Dict

import keyboard
import numpy as np
import pyaudio
import requests
import romajitable
import speech_recognition as sr
import torch.cuda
import whisper
from pydub import AudioSegment
from speech_recognition import AudioData

import chatbot
import dict
import streamChat
import subLocal as SUB
from deep_translator import GoogleTranslator
from timer import Timer


def load_config():
    try:
        with open("config.json", "r") as json_file:
            data = json.load(json_file)
            print(json.dumps(data, indent=2))

            global VOICE_VOX_URL_LOCAL
            VOICE_VOX_URL_LOCAL = data['voicevox_local_url']
            global voicevox_api_key
            voicevox_api_key = data['voicevox_api_key']
            global use_cloud_voicevox
            use_cloud_voicevox = data['use_cloud_voicevox']
            global use_elevenlab
            use_elevenlab = data['use_elevenlab']
            global elevenlab_api_key
            elevenlab_api_key = data['elevenlab_api_key']
            streamChat.twitch_access_token = data['twitch_access_token']
            streamChat.twitch_channel_name = data['twitch_channel_name']
            streamChat.youtube_video_id = data['youtube_video_id']
            global use_voicevox
            use_voicevox = data['use_voicevox']
            global VALL_E_X_URL
            VALL_E_X_URL = data['vall_e_x_url']

            if elevenlab_api_key == '':
                elevenlab_api_key = os.getenv("ELEVENLAB_API_KEY")

    except:
        print("Unable to load JSON file.")
        print(traceback.format_exc())


def save_config(key, value):
    try:
        with open("config.json", "r") as json_file:
            config = json.load(json_file)
            config[key] = value
            print(f"config[{key}] = {value}")
        with open("config.json", "w") as json_file:
            json_object = json.dumps(config, indent=4)
            json_file.write(json_object)
    except:
        print("Unable to load JSON file.")
        print(traceback.format_exc())

def translate(text, from_code, to_code):
    if use_voicevox:
        return GoogleTranslator(source=from_code, target=to_code).translate(text)
    else:
        return text


input_device_id = None
output_device_id = [None, None]

VOICE_VOX_URL_HIGH_SPEED = "https://api.su-shiki.com/v2/voicevox/audio/"
VOICE_VOX_URL_LOW_SPEED = "https://api.tts.quest/v1/voicevox/"
VOICE_VOX_URL_LOCAL = "127.0.0.1:50021"
VALL_E_X_URL = '127.0.0.1:6000'

VOICE_OUTPUT_FILENAME = "audioResponse.wav"

use_elevenlab = False
elevenlab_api_key = ''
elevenlab_voice_id = ''
use_cloud_voicevox = False
use_voicevox = False
voicevox_api_key = ''
speakersResponse: Optional[Dict] = None
voicevox_server_started = False
speaker_id = 1
mic_mode = 'open mic'
MIC_OUTPUT_FILENAME = "PUSH_TO_TALK_OUTPUT_FILE.wav"
PUSH_TO_RECORD_KEY = '5'
use_ingame_push_to_talk_key = False
ingame_push_to_talk_key = 'f'

whisper_filter_list = ['you', 'thank you.', 'thanks for watching.', '你']
pipeline_elapsed_time = 0
TTS_pipeline_start_time = 0
pipeline_timer = Timer()
step_timer = Timer()
model: whisper.model.Whisper
voicevox_process: subprocess.Popen

is_show_voicevox_connect_warn = False

def initialize_model():
    global model
    model = whisper.load_model("base", device='cuda' if torch.cuda.is_available() else 'cpu')


def connect_voicevox_server():
    global voicevox_server_started, voicevox_process
    url = f"http://{VOICE_VOX_URL_LOCAL}/version"

    try:
        response = requests.request("GET", url)
    except:
        voicevox_server_started = False
        return False

    if response.status_code == 200:
        voicevox_server_started = True
        return True
    voicevox_server_started = False
    return False


def initialize_speakers():
    global speakersResponse, is_show_voicevox_connect_warn
    if not voicevox_server_started:
        if not connect_voicevox_server():
            if not is_show_voicevox_connect_warn:
                print("voicevox_engine didn't start!")
                print("Can't initialize speakers!")
                is_show_voicevox_connect_warn = True
            return
    url = f"http://{VOICE_VOX_URL_LOCAL}/speakers"
    while True:
        try:
            response = requests.request("GET", url)
            break
        except:
            print("Waiting for voicevox to start... ")
            time.sleep(0.5)
    speakersResponse = response.json()


def get_speaker_names():
    global speakersResponse
    if speakersResponse is None:
        initialize_speakers()
    try:
        speakerNames = list(map(lambda speaker: speaker['name'],  speakersResponse))
        return speakerNames
    except:
        return ['No data!']


def get_speaker_styles(speaker_name):
    global speakersResponse
    if speakersResponse is None:
        initialize_speakers()
    try:
        speaker_styles = next(speaker['styles'] for speaker in speakersResponse if speaker['name'] == speaker_name)

        print(speaker_styles)
        return speaker_styles
    except:
        return [
            {
                'name': 'No data!',
                'id': 'No data!'
            }
        ]


recording = False
auto_recording = False
logging_eventhandlers = []

voice_name = '四国めたん'
input_language_name = 'English'

# Stores variable for play original function
last_input_text = ''
last_voice_param = None
last_input_language = ''

language_dict = dict.language_dict


def start_record_auto():
    log_message("Recording...")
    global auto_recording
    auto_recording = True
    thread = Thread(target=start_STTS_loop)
    thread.start()


def start_record_auto_chat():
    log_message("Recording...")
    global auto_recording
    auto_recording = True
    thread = Thread(target=start_STTS_loop_chat)
    thread.start()


def stop_record_auto():
    global auto_recording
    auto_recording = False
    log_message("Recording Stopped")


def cloud_synthesize(text, speaker_id, api_key=''):
    global pipeline_elapsed_time
    url: str
    if api_key == '':
        print('No api key detected, sending request to low speed server.')
        url = f"{VOICE_VOX_URL_LOW_SPEED}?text={text}&speaker={speaker_id}"
    else:
        print(
            f'Api key {api_key} detected, sending request to high speed server.')
        url = f"{VOICE_VOX_URL_HIGH_SPEED}?text={text}&speaker={speaker_id}&key={api_key}"
    print(f"Sending POST request to: {url}")
    try:
        response = requests.request(
            "POST", url)
        print(f'response: {response}')

        wav_bytes: bytes
        if api_key == '':
            response_json = response.json()

            try:
                # download wav file from response
                wav_url = response_json['wavDownloadUrl']
            except:
                print("Failed to get wav download link.")
                print(response_json)
                return False
            print(f"Downloading wav response from {wav_url}")
            wav_bytes = requests.get(wav_url).content
        else:
            wav_bytes = response.content

        with open(VOICE_OUTPUT_FILENAME, "wb") as file:
            file.write(wav_bytes)
        return True
    except:
        return False


def vall_e_x_synthesize(text, lang):
    try:
        response = requests.request("POST", f'http://{VALL_E_X_URL}/synthesize_long', params={
            'text': text,
            'lang': lang,
            'prompt': '春日部つむぎ'
        })

        with open(VOICE_OUTPUT_FILENAME, "wb") as file:
            file.write(base64.b64decode(response.json()['data'].encode()))
        return True
    except:
        print("vall_e_x server doesn't start!")
        return False


def synthesize_audio(text, speaker_id):
    global use_cloud_voicevox, voicevox_api_key, use_elevenlab, use_voicevox
    if use_elevenlab:
        return elevenlab_synthesize(text)
    elif use_voicevox:
        if use_cloud_voicevox:
            return cloud_synthesize(text, speaker_id, api_key=voicevox_api_key)
        else:
            return no_api_cloud_synthesize(text, speaker_id)
    else:
        return vall_e_x_synthesize(text, 'zh' if dict.language_dict[input_language_name].startswith('zh') else dict.language_dict[input_language_name])


def no_api_cloud_synthesize(text, speaker_id):
    if voicevox_server_started:
        VoiceTextResponse = requests.request(
            "POST", f"http://{VOICE_VOX_URL_LOCAL}/audio_query?text={text}&speaker={speaker_id}")
        AudioResponse = requests.request(
            "POST", f"http://{VOICE_VOX_URL_LOCAL}/synthesis?speaker={speaker_id}", data=VoiceTextResponse)

        with open(VOICE_OUTPUT_FILENAME, "wb") as file:
            file.write(AudioResponse.content)
        return True
    else:
        print("voicevox server didn't start!")
        return False


def elevenlab_synthesize(message):

    global elevenlab_api_key
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{elevenlab_voice_id}'
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': elevenlab_api_key,
        'Content-Type': 'application/json'
    }
    data = {
        'text': message,
        'voice_settings': {
            'stability': 0.75,
            'similarity_boost': 0.75
        }
    }
    print(f"Sending POST request to: {url}")
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        print(response)
        audio_content = AudioSegment.from_file(
            io.BytesIO(response.content), format="mp3")
        audio_content.export(VOICE_OUTPUT_FILENAME, 'wav')
        return True
    except:
        return False

def PlayAudio():
    global output_device_id
    # open the file for reading.
    wf = wave.open(VOICE_OUTPUT_FILENAME, 'rb')

    # create an audio object
    p = [pyaudio.PyAudio(), pyaudio.PyAudio()]

    # length of data to read.
    chunk = 1024
    # open stream based on the wave object which has been input.
    stream = []
    for index, id in enumerate(set(output_device_id)):
        stream.append(p[index].open(format=p[index].get_format_from_width(wf.getsampwidth()),
                               channels=wf.getnchannels(),
                               rate=wf.getframerate(),
                               output=True,
                               output_device_index=id))
    assert len(stream)==len(set(output_device_id)), f'{len(stream)}, {set(output_device_id)}'
    # read data (based on the chunk size)
    data = wf.readframes(chunk)

    # play stream (looping from beginning of file to the end)
    while data:
        # writing to the stream is what *actually* plays the sound.
        for s in stream:
            s.write(data)
        data = wf.readframes(chunk)

    # cleanup stuff.
    wf.close()
    for s in stream:
        s.close()
    p[0].terminate(), p[1].terminate()
    SUB.send_update_text_event('')


def push_to_talk():
    while True:
        a = keyboard.read_key()
        if a == PUSH_TO_RECORD_KEY:
            log_message(f"push to talk started...")
            audio = pyaudio.PyAudio()
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 44100
            # Open audio stream
            global input_device_id
            stream = audio.open(format=FORMAT, channels=CHANNELS,
                                rate=RATE, input=True,
                                frames_per_buffer=CHUNK, input_device_index=input_device_id)

            # Initialize frames array to store audio data
            frames = []

            # Record audio data
            while True:
                data = stream.read(CHUNK)
                frames.append(data)
                if not keyboard.is_pressed(PUSH_TO_RECORD_KEY):
                    break

            # Stop recording and close audio stream
            log_message("push to talk ended")
            stream.stop_stream()
            stream.close()

            # Save recorded audio data to file
            audio_segment = AudioSegment(
                data=b''.join(frames),
                sample_width=audio.get_sample_size(FORMAT),
                frame_rate=RATE,
                channels=CHANNELS
            )

            audio_segment.export(MIC_OUTPUT_FILENAME, format="wav")
            break


def start_STTS_loop():
    global auto_recording
    while auto_recording:
        start_STTS_pipeline()


def start_STTS_loop_chat():
    global auto_recording
    while auto_recording:
        start_STTS_pipeline(use_chatbot=True)


def start_STTS_pipeline(use_chatbot=False):
    global pipeline_elapsed_time
    global step_timer
    global pipeline_timer
    global mic_mode
    audio: Union[AudioData, np.ndarray]
    if mic_mode == 'open mic':
        # record audio
        # obtain audio from the microphone
        r = sr.Recognizer()
        global input_device_id
        with sr.Microphone(device_index=input_device_id) as source:
            log_message("Say something!")
            audio = r.listen(source)

        global auto_recording
        if not auto_recording:
            return

        with open(MIC_OUTPUT_FILENAME, "wb") as file:
            file.write(audio.get_wav_data())
    elif mic_mode == 'push to talk':
        push_to_talk()
    log_message("recording complete, sending to whisper")

    # send audio to whisper
    pipeline_timer.start()
    step_timer.start()
    input_text = ''
    try:
        global model
        if model is None:
            initialize_model()
        global input_language_name
        print(input_language_name)
        audio = whisper.load_audio(MIC_OUTPUT_FILENAME)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(model.device)
        options = whisper.DecodingOptions(
            language=input_language_name.lower(),
            without_timestamps=True,
            fp16=False if model.device == 'cpu' else None,
            task='translate' if input_language_name != 'English' else 'transcribe')
        result = whisper.decode(model, mel, options)
        input_text = result.text
    except sr.UnknownValueError:
        log_message("Whisper could not understand audio")
    except sr.RequestError:
        log_message("Could not request results from Whisper")
    global whisper_filter_list
    if input_text == '':
        return
    log_message(f'Input: {input_text} ({step_timer.end()}s)')

    print(f'looking for {input_text.strip().lower()} in {whisper_filter_list}')
    if input_text.strip().lower() in whisper_filter_list:
        log_message(f'Input {input_text} was filtered.')
        return
    with open("input.txt", "w", encoding="utf-8") as file:
        file.write(input_text)
    pipeline_elapsed_time += pipeline_timer.end()
    if use_chatbot:
        log_message("recording complete, sending to chatbot")
        chatbot.send_user_input(input_text)
    else:
        SUB.send_update_text_event(input_text)
        start_TTS_pipeline(input_text)


def start_TTS_pipeline(input_text):
    global voice_name
    global speaker_id
    global pipeline_elapsed_time
    pipeline_timer.start()
    inputLanguage = language_dict[input_language_name]
    if use_elevenlab:
        outputLanguage = 'en'
    else:
        outputLanguage = 'ja'
    print(f"input Language: {inputLanguage}, output Language: {outputLanguage}")
    need_translate = inputLanguage != outputLanguage
    if need_translate:
        step_timer.start()
        input_processed_text = translate(input_text, inputLanguage, outputLanguage)
        log_message(f'Translation: {input_processed_text} ({step_timer.end()}s)')
    else:
        input_processed_text = input_text

    # filter special characters
    filtered_text = ''
    for char in input_processed_text:
        if char != "*":
            filtered_text += char

    with open("translation.txt", "w", encoding="utf-8") as file:
        file.write(filtered_text)
    step_timer.start()
    if synthesize_audio(filtered_text, speaker_id):
        log_message(
            f"Speech synthesized for text [{filtered_text}] ({step_timer.end()}s)")
        log_message(
            f'Total time: ({round(pipeline_elapsed_time + pipeline_timer.end(),2)}s)')
        print(f"ingame_push_to_talk_key: {ingame_push_to_talk_key}")
        global use_ingame_push_to_talk_key
        if use_ingame_push_to_talk_key and ingame_push_to_talk_key != '':
            keyboard.press(ingame_push_to_talk_key)
        PlayAudio()
        if use_ingame_push_to_talk_key and ingame_push_to_talk_key != '':
            keyboard.release(ingame_push_to_talk_key)
        global last_input_text
        last_input_text = input_text
        global last_input_language
        last_input_language = inputLanguage
        global last_voice_param
        last_voice_param = speaker_id
        pipeline_elapsed_time = 0


def playOriginal():
    global last_input_text
    global last_voice_param
    global last_input_language
    global input_language_name
    inputLanguage = language_dict[input_language_name]
    if last_input_language != 'en':
        last_input_text_processed = translate(last_input_text, inputLanguage, 'en')
    else:
        last_input_text_processed = last_input_text
    text_ja = last_input_text_processed
    if use_voicevox:
        text_ja = romajitable.to_kana(last_input_text_processed).katakana
        text_ja = text_ja.replace('・', '')
    synthesize_audio(text_ja, last_voice_param)
    log_message(f'playing input: {text_ja}')
    PlayAudio()


def log_message(message_text):
    print(message_text)
    global logging_eventhandlers
    for eventhandler in logging_eventhandlers:
        eventhandler(message_text)


def change_input_language(input_lang_name):
    global input_language_name
    input_language_name = input_lang_name