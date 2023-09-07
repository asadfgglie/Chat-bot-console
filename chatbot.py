import os
import re
import traceback
import openai
import requests

import STTSLocal as STTS
import subLocal as SUB

user_name = '朝歌'
AI_name = 'LiuLi'
openai_api_key = ''
use_text_generation_web_ui = False
AI_RESPONSE_FILENAME = 'ai-response.txt'
is_talk = True
max_no_talking_time = 10
min_no_talking_time = 1

lore = ''
try:
    with open('./lore.txt', 'r', encoding='utf-8') as file:
        lore = file.read()
except Exception:
    print("error when reading lore.txt")
    print(traceback.format_exc())
lore = lore.replace('\n', '')

message_log = [
    {"role": "system", "content": lore},
    {"role": "user", "content": lore},
] # for openAI API

history = {
    'internal': [],
    'visible': []
} # for text-generation-ui API

logging_eventhandlers = []

is_random_dialog_running = False


def send_user_input(user_input, _continue=False, _regenerate=False):
    log_message(f'{user_name}: {user_input}')
    global message_log, openai_api_key, history, is_talk

    if not use_text_generation_web_ui:
        if _regenerate:
            message_log.pop()
            message_log.pop()
        if not _continue:
            message_log.append({"role": "user", "content": user_input})
        if openai_api_key == '':
            openai_api_key = os.getenv("OPENAI_API_KEY")

        openai.api_key = openai_api_key
        print(f"Sending: {user_input} with api key :{openai_api_key}")
        print(message_log)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message_log
            )
        except Exception:
            log_message("Error when loading api key from environment variable")
            log_message(
                "You need an API key from https://platform.openai.com/ stored in an environment variable with name \"OPENAI_API_KEY\" to use the chat feature")
            print(traceback.format_exc())
            return
        text_response = response['choices'][0]['message']['content']
        if _continue:
            message_log[-1]['content'] += text_response
        else:
            message_log.append({"role": "assistant", "content": text_response})
    else:
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
        response = requests.post(URI, json=request)

        if response.status_code == 200:
            history = response.json()['results'][0]['history']
            text_response = history['visible'][-1][1]
            print(history)
        else:
            print(response.status_code)
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


# def separate_sentences(text):
#     # Define common sentence-ending punctuation marks
#     sentence_ends = re.compile(r'[.!?]+')
#
#     # Replace any newline characters with spaces
#     text = text.replace('\n', ' ')
#
#     # Split text into list of strings at each sentence-ending punctuation mark
#     sentences = sentence_ends.split(text)
#
#     # Join sentences with newline character
#     result = '\n'.join(sentences)
#
#     return result

def remove_surrounded_chars(string):
    # this expression matches to 'as few symbols as possible (0 upwards) between any asterisks' OR
    # 'as few symbols as possible (0 upwards) between an asterisk and the end of the string'
    return re.sub("\*[^\\\*]*?(\*|$)", '', string)