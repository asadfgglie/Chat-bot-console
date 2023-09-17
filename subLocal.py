import time
from queue import Queue
from threading import Thread

import _queue

text_change_eventhandlers = []

is_running = False

text_queue = Queue()


def start():
    global is_running
    is_running = True
    Thread(target=show_text_loop).start()


def stop():
    global is_running
    is_running = False

def show_text_loop():
    global is_running
    while is_running:
        try:
            text = text_queue.get_nowait()
            print(f'Subtitle: {text}')
            global text_change_eventhandlers
            for eventhandler in text_change_eventhandlers:
                eventhandler(text)
            time.sleep(2 + len(text) / 2)
        except _queue.Empty:
            time.sleep(0.1)

def send_update_text_event(text):
    text_queue.put(text, block=False, timeout=None)