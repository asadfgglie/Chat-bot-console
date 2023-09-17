import re

import requests

import STTSLocal as STTS
import subLocal as SUB

user_name = '朝歌'
AI_name = 'LiuLi'

AI_RESPONSE_FILENAME = 'ai-response.txt'
is_talk = True
max_no_talking_time = 10 # min
min_no_talking_time = 1 # min

history = {
    'internal': [],
    'visible': []
} # for text-generation-ui API

logging_eventhandlers = []

is_random_dialog_running = False


def send_user_input(user_input, _continue=False, _regenerate=False):
    log_message(f'{user_name}: {user_input}')
    global history, is_talk


    HOST = 'localhost:5000'
    URI = f'http://{HOST}/api/v1/chat'
    request = {
        'user_input': user_input,
        'max_new_tokens': 250,
        'auto_max_new_tokens': False,
        'history': history,
        'mode': 'chat',  # Valid options: 'chat', 'chat-instruct', 'instruct'
        'character': 'LiuLi',
        'instruction_template': 'Llama-v2',  # Will get autodetect if unset
        'your_name': user_name,
        'name1': user_name, # Optional
        'name2': AI_name, # Optional
        'regenerate': _regenerate,
        '_continue': _continue,
        'chat_instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\n\n<|prompt|>',
        'preset': 'Midnight Enigma',
        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 2048,
        'ban_eos_token': False,
        'skip_special_tokens': True,
        'stopping_strings': []
    }
    print(f"Sending: {user_input} to text-generation-ui")
    try:
        response = requests.post(URI, json=request)

        if response.status_code == 200:
            history = response.json()['results'][0]['history']
            text_response = history['visible'][-1][1]
            print(history)
        else:
            print(response.status_code)
            return
    except requests.exceptions.ConnectionError as e:
        print(e)
        return

    is_talk = True
    log_message(f'{AI_name}: {text_response}')
    SUB.send_update_text_event(text_response)
    with open(AI_RESPONSE_FILENAME, "w", encoding="utf-8") as file:
        file.write(text_response)
    STTS.start_TTS_pipeline(remove_surrounded_chars(text_response))


def log_message(message_text):
    print(message_text)
    global logging_eventhandlers
    for eventhandler in logging_eventhandlers:
        eventhandler(message_text)

def remove_surrounded_chars(string):
    # this expression matches to 'as few symbols as possible (0 upwards) between any asterisks' OR
    # 'as few symbols as possible (0 upwards) between an asterisk and the end of the string'
    return re.sub("\*[^\\\*]*?(\*|$)", '', string)