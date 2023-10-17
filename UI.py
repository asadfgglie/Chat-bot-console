import json
import os
import random
import time
from enum import Enum
from threading import Event
from threading import Thread
from typing import Optional

import customtkinter
import keyboard
import numpy as np
import sounddevice as sd

import STTSLocal as STTS
import chatbot
import dict
import settings
import streamChat
import subLocal as SUB


class Pages(Enum):
    AUDIO_INPUT = 0
    TEXT_INPUT = 1
    SETTINGS = 2
    SUBTITLE = 3
    CHAT = 4
    STREAM = 5


current_page = Pages.AUDIO_INPUT
pageChange_eventhandlers = []
option_menu_list: list['OptionsFrame'] = []
option_frame_list: list['OptionsFrame'] = []
audio_level = 0.3

mic_meters: list['AudiodeviceSelection'] = []




class Microphone:
    def __init__(self, device=None):
        self.stream = sd.InputStream(callback=self.callback)
        self.volume = 0.3
        self.device = device
        self.thread = Thread(target=self.start, daemon=True)

    def start(self, device):
        self.device = device
        if self.stream is not None:
            self.stream.stop()
        self.stream = sd.InputStream(
            device=self.device, callback=self.callback)
        self.stream.start()
        while True:
            sd.sleep(1000)

    def start_thread(self, device=None):
        self.thread = Thread(target=self.start, args=(device,), daemon=True)
        self.thread.start()

    def callback(self, indata, _frames, _time, _status):
        self.volume = np.linalg.norm(indata) * 0.1


class SidebarFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        global current_page
        super().__init__(master, **kwargs)

        Audio_input_Button = customtkinter.CTkButton(master=self,
                                                     width=120,
                                                     height=32,
                                                     border_width=0,
                                                     corner_radius=0,
                                                     text="Audio input",
                                                     command=lambda: self.change_page(
                                                         Pages.AUDIO_INPUT),
                                                     fg_color='grey'
                                                     )
        Audio_input_Button.pack(anchor="s")
        # add widgets onto the frame...
        text_input_button = customtkinter.CTkButton(master=self,
                                                    width=120,
                                                    height=32,
                                                    border_width=0,
                                                    corner_radius=0,
                                                    text="Text input",
                                                    command=lambda: self.change_page(
                                                        Pages.TEXT_INPUT),
                                                    fg_color='grey'
                                                    )
        text_input_button.pack(anchor="s")

        subtitles_button = customtkinter.CTkButton(master=self,
                                                   width=120,
                                                   height=32,
                                                   border_width=0,
                                                   corner_radius=0,
                                                   text="Subtitles",
                                                   command=lambda: self.change_page(
                                                        Pages.SUBTITLE),
                                                   fg_color='grey'
                                                   )
        subtitles_button.pack(anchor="s")

        chat_button = customtkinter.CTkButton(master=self,
                                              width=120,
                                              height=32,
                                              border_width=0,
                                              corner_radius=0,
                                              text="Chat",
                                              command=lambda: self.change_page(
                                                  Pages.CHAT),
                                              fg_color='grey'
                                              )
        chat_button.pack(anchor="s")

        stream_button = customtkinter.CTkButton(master=self,
                                                width=120,
                                                height=32,
                                                border_width=0,
                                                corner_radius=0,
                                                text="Stream",
                                                command=lambda: self.change_page(
                                                    Pages.STREAM),
                                                fg_color='grey'
                                                )
        stream_button.pack(anchor="s")

        button = customtkinter.CTkButton(master=self,
                                         width=120,
                                         height=32,
                                         border_width=0,
                                         corner_radius=0,
                                         text="Settings",
                                         command=lambda: self.change_page(
                                             Pages.SETTINGS),
                                         fg_color='grey'
                                         )
        button.pack(anchor="s")

    @staticmethod
    def change_page(page):
        global current_page
        current_page = page

        global pageChange_eventhandlers
        for eventhandler in pageChange_eventhandlers:
            eventhandler()


class ConsoleFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.isRecording = False
        self.stop_recording_event = Event()
        self.thread = Thread(target=STTS.start_record_auto,
                             args=(self.stop_recording_event,))
        # add widgets onto the frame...
        self.textbox = customtkinter.CTkTextbox(self, width=400, height=400)
        self.textbox.grid(row=0, column=0, rowspan=2, columnspan=3)
        # configure textbox to be read-only
        self.textbox.configure(state="disabled")
        STTS.logging_eventhandlers.append(self.log_message_on_console)

        self.recordButton = customtkinter.CTkButton(master=self,
                                                    width=0,
                                                    height=32,
                                                    border_width=0,
                                                    corner_radius=8,
                                                    text="Start Recording",
                                                    command=self.recordButton_callback,
                                                    fg_color='grey'
                                                    )
        self.recordButton.grid(row=3, column=0, pady=10)

        self.playOriginalButton = customtkinter.CTkButton(master=self,
                                                          width=120,
                                                          height=32,
                                                          border_width=0,
                                                          corner_radius=8,
                                                          text="Play original",
                                                          command=self.play_original_callback,
                                                          fg_color='grey'
                                                          )
        self.playOriginalButton.grid(row=3, column=1, pady=10)

        self.clearConsoleButton = customtkinter.CTkButton(master=self,
                                                          width=32,
                                                          height=32,
                                                          border_width=0,
                                                          corner_radius=8,
                                                          text="X",
                                                          command=self.clear_console,
                                                          fg_color='grey'
                                                          )
        self.clearConsoleButton.grid(row=3, column=2, padx=10, pady=10)

    def clear_console(self):
        self.textbox.configure(state="normal")
        self.textbox.delete('1.0', customtkinter.END)
        self.textbox.configure(state="disabled")

    def recordButton_callback(self):
        if self.isRecording:
            self.recordButton.configure(
                text="Start Recording", fg_color='grey')
            self.isRecording = False
            STTS.stop_record_auto()
        else:
            self.recordButton.configure(
                text="Stop Recording", fg_color='#fc7b5b')
            self.isRecording = True
            STTS.start_record_auto()
        self.recordButton.grid(row=3, column=0, pady=10)

    @staticmethod
    def play_original_callback():
        thread = Thread(target=STTS.playOriginal())
        thread.start()

    def log_message_on_console(self, message_text):
        # insert at line 0 character 0
        self.textbox.configure(state="normal")
        self.textbox.insert(customtkinter.INSERT, message_text+'\n')
        self.textbox.configure(state="disabled")
        self.textbox.see("end")


class ChatFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.no_talking_time = 60 * (random.random() * 9 + 1)
        self.isRecording = False
        self.thread = Thread(target=STTS.start_record_auto)

        self.textbox = customtkinter.CTkTextbox(self, width=400, height=325, maxundo=-1, undo=True)
        self.textbox.grid(row=0, column=0, rowspan=3, columnspan=4)
        self.textbox.configure(state="disabled")

        chatbot.logging_eventhandlers.append(self.log_message_on_console)

        self.user_input_var = customtkinter.StringVar(self, '')
        self.user_input = customtkinter.CTkEntry(master=self, textvariable=self.user_input_var, width=200)
        self.user_input.grid(row=3, column=0, padx=(10,0), pady=(10,0), sticky='W', columnspan=2)
        self.user_input.bind('<Return>', self.send_user_input)
        self.user_input.focus_set()

        self.send_button = customtkinter.CTkButton(master=self,
                                                   width=32,
                                                   height=32,
                                                   border_width=0,
                                                   corner_radius=8,
                                                   text="send",
                                                   command=self.send_user_input,
                                                   fg_color='grey')
        self.send_button.grid(row=3, column=2, pady=(10,0), padx=(5,0))

        self.recordButton = customtkinter.CTkButton(master=self,
                                                    width=120,
                                                    height=32,
                                                    border_width=0,
                                                    corner_radius=8,
                                                    text="Start Recording",
                                                    command=self.recordButton_callback,
                                                    fg_color='grey')
        self.recordButton.grid(row=3, column=3, pady=(10,0), padx=(5,5))

        self.regenerateButton = customtkinter.CTkButton(master=self,
                                                        width=0,
                                                        height=32,
                                                        border_width=0,
                                                        corner_radius=8,
                                                        text="Regenerate",
                                                        command=self.regenerate_callback,
                                                        fg_color='grey')
        self.regenerateButton.grid(row=4, column=0, pady=(10,0), padx=(5,0))

        self.remove_lastButton = customtkinter.CTkButton(master=self,
                                                         width=0,
                                                         height=32,
                                                         border_width=0,
                                                         corner_radius=8,
                                                         text="Remove last",
                                                         command=self.remove_last_callback,
                                                         fg_color='grey')
        self.remove_lastButton.grid(row=4, column=1, pady=(10,0), padx=(5,0))

        self.continueButton = customtkinter.CTkButton(master=self,
                                                      width=0,
                                                      height=32,
                                                      border_width=0,
                                                      corner_radius=8,
                                                      text="Continue",
                                                      command=self.continue_callback,
                                                      fg_color='grey')
        self.continueButton.grid(row=4, column=2, pady=(10,0), padx=(5,0))

        self.clear_historyButton = customtkinter.CTkButton(master=self,
                                                           width=0,
                                                           height=32,
                                                           border_width=0,
                                                           corner_radius=8,
                                                           text="Clear history",
                                                           command=self.clear_history_callback,
                                                           fg_color='grey')
        self.clear_historyButton.grid(row=4, column=3, pady=(10,0), padx=(5,5))

        self.start_random_dialog_loopButton = customtkinter.CTkButton(master=self,
                                                                      width = 0,
                                                                      height = 32,
                                                                      border_width = 0,
                                                                      corner_radius = 8,
                                                                      text = "Start random dialog thread",
                                                                      command = self.start_random_dialog_loop_callback,
                                                                      fg_color = 'grey')
        self.start_random_dialog_loopButton.grid(row=5, column=1, pady=(10,0), padx=(5,5), columnspan=2)

    def start_random_dialog_loop_callback(self):
        if not chatbot.is_random_dialog_running:
            self.start_random_dialog_loopButton.configure(text="Stop random dialog", fg_color='#fc7b5b')
            chatbot.is_random_dialog_running = True
            print('Start random dialog')
            Thread(target=self.start_random_dialog_loop).start()
        else:
            self.start_random_dialog_loopButton.configure(text="Start random dialog", fg_color='grey')
            chatbot.is_random_dialog_running = False
            print('Stop random dialog')
            self.clear_history_callback()

    def start_random_dialog_loop(self):
        self.clear_history_callback()
        self.user_input_var.set('')
        self.send_user_input()
        while chatbot.is_random_dialog_running:
            self.wait_no_talking()
            if chatbot.is_random_dialog_running:
                self.clear_history_callback()
                self.user_input_var.set('')
                self.send_user_input()


    def clear_history_callback(self):
        self.textbox.configure(state=customtkinter.NORMAL)
        self.textbox.delete('1.0', customtkinter.END)
        self.textbox.configure(state=customtkinter.DISABLED)

        if len(chatbot.history['internal']) > 0:
            os.makedirs('./log/', exist_ok=True)
            os.makedirs('./log/dataset/', exist_ok=True)
            with open(f'./log/{time.strftime(f"{chatbot.user_name}_to_{chatbot.AI_name}_%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))}.json', 'w') as f:
                f.write(json.dumps(chatbot.history, indent=2))
            with open(f'./log/dataset/{time.strftime(f"{chatbot.user_name}_to_{chatbot.AI_name}_%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))}.json', 'w') as f:
                tmp = []
                for index, turn in enumerate(chatbot.history['internal']):
                    user_input, bot_response = turn
                    if user_input != '':
                        tmp.append({
                            'user_name': chatbot.user_name,
                            'input': user_input,
                            'bot_name': chatbot.AI_name,
                            'output': bot_response
                        })
                    if user_input == '' and index == 0:
                        tmp.append({
                            'user_name': chatbot.user_name,
                            'input': 'Do you have any interesting stories to share with me?',
                            'bot_name': chatbot.AI_name,
                            'output': bot_response
                        })
                f.write(json.dumps(tmp, indent=2))

        chatbot.history = {
            'internal': [],
            'visible': []
        }

    def remove_last_callback(self):
        self.textbox.configure(state=customtkinter.NORMAL)
        tmp = self.textbox.get('1.0', customtkinter.END)
        self.textbox.delete('1.0', customtkinter.END)
        self.textbox.insert('1.0', tmp[:tmp.rfind(f'{chatbot.user_name}: ') if tmp.rfind(f'{chatbot.user_name}: ') != -1 else tmp.rfind(f'{chatbot.AI_name}: ')])
        self.textbox.configure(state=customtkinter.DISABLED)

        try:
            last_user_input = chatbot.history['internal'].pop()[0]
            chatbot.history['visible'].pop()

            self.user_input.delete(0, customtkinter.END)
            self.user_input.insert(0, last_user_input)
        except IndexError:
            print("Chat history is empty! Can't get back user input!")

    def continue_callback(self):
        self.textbox.configure(state=customtkinter.NORMAL)
        tmp = self.textbox.get('1.0', customtkinter.END)
        self.textbox.delete('1.0', customtkinter.END)
        self.textbox.insert('1.0', tmp[:tmp.rfind(f'{chatbot.user_name}: ') if tmp.rfind(f'{chatbot.user_name}: ') != -1 else tmp.rfind(f'{chatbot.AI_name}: ')])
        self.textbox.configure(state=customtkinter.DISABLED)

        try:
            last_user_input = chatbot.history['internal'][-1][0]

            thread = Thread(target=chatbot.send_user_input, args=[last_user_input, True])
            thread.start()
        except IndexError:
            print("Chat history is empty! Can't continue the conversation!")

    def regenerate_callback(self):
        self.textbox.configure(state=customtkinter.NORMAL)
        tmp = self.textbox.get('1.0', customtkinter.END)
        self.textbox.delete('1.0', customtkinter.END)
        self.textbox.insert('1.0', tmp[:tmp.rfind(f'{chatbot.user_name}: ') if tmp.rfind(f'{chatbot.user_name}: ') != -1 else tmp.rfind(f'{chatbot.AI_name}: ')])
        self.textbox.configure(state=customtkinter.DISABLED)

        try:
            last_user_input = chatbot.history['internal'][-1][0]

            thread = Thread(target=chatbot.send_user_input, args=[last_user_input, False, True])
            thread.start()
        except IndexError:
            print("Chat history is empty! Can't regenerate response!")

    def recordButton_callback(self):
        if self.isRecording:
            self.recordButton.configure(
                text="Start Recording", fg_color='grey')
            self.isRecording = False
            STTS.stop_record_auto()
        else:
            self.recordButton.configure(
                text="Stop Recording", fg_color='#fc7b5b')
            self.isRecording = True
            STTS.start_record_auto_chat()

    def send_user_input(self, _=None):
        text = self.user_input_var.get()
        self.user_input_var.set('')
        thread = Thread(target=chatbot.send_user_input, args=[text,])
        thread.start()

    def log_message_on_console(self, message_text):
        # insert at line 0 character 0
        self.textbox.configure(state="normal")
        self.textbox.insert(customtkinter.INSERT, message_text+'\n')
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    def wait_no_talking(self):
        while self.no_talking_time > 0:
            if chatbot.is_random_dialog_running:
                if chatbot.is_talk:
                    self.no_talking_time += 60
                    chatbot.is_talk = False
                self.no_talking_time -= 1
                time.sleep(1)
            else:
                break
        self.no_talking_time = 60 * (random.random() * (chatbot.max_no_talking_time - chatbot.min_no_talking_time) + chatbot.min_no_talking_time)


class TextBoxFrame(customtkinter.CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.default_message = "Hello, how are you doing?"
        self.text_input = customtkinter.CTkTextbox(self, width=400, height=400)
        self.text_input.grid(row=0, column=0, rowspan=2, columnspan=2)
        self.text_input.insert(customtkinter.INSERT, self.default_message+'\n')
        self.synthesizeButton = customtkinter.CTkButton(master=self,
                                                        width=120,
                                                        height=32,
                                                        border_width=0,
                                                        corner_radius=8,
                                                        text="Synthesize",
                                                        command=self.synthesizeButton_callback,
                                                        fg_color='grey'
                                                        )
        self.synthesizeButton.grid(
            row=3, column=0, padx=10, pady=10, sticky="w")

    def synthesizeButton_callback(self):
        SUB.send_update_text_event(self.text_input.get("1.0", customtkinter.END))
        STTS.start_TTS_pipeline(self.text_input.get("1.0", customtkinter.END))


class AudiodeviceSelection(customtkinter.CTkFrame):
    # set_command is called with updated device_id
    # get_command should return the device_id for the mic meter
    # device_type can be None, input or output for device filtering
    def __init__(self, set_command, get_command, master, device_type=None, show_device_selection=True, show_driver_selection=True, show_mic_meter=True, index=None, **kwargs):
        super().__init__(master, **kwargs)
        # Mic meter
        self._subtitle_mic_stream = None
        self.set_command = set_command
        self.get_command = get_command
        self.audio_level = 0.3
        self.device_type = device_type
        self.index = index
        # driver selection
        if show_driver_selection:
            audio_driver_label = customtkinter.CTkLabel(
                master=self, text='Audio driver: ')
            audio_driver_label.grid(
                row=0, column=0, padx=10, pady=10, sticky='W')
            self.audio_drivers = self.get_audio_drivers()
            self.audio_driver_names = list(
                map(lambda driver: driver['name'], self.audio_drivers))
            # If the driver name in settings can be found, use the settings
            driver_setting = ''
            if device_type == 'input':
                driver_setting = settings.get_settings('input_audio_driver')
            elif device_type == 'output':
                driver_setting = settings.get_settings(f'output_audio_driver_{self.index}')
            self.default_driver = self.audio_driver_names[0]
            print(
                f'Looking for \'{driver_setting}\' in {self.audio_driver_names}.')
            if driver_setting in self.audio_driver_names:
                print("found")
                self.default_driver = driver_setting
            self.audio_input_combobox_var = customtkinter.StringVar(
                value=self.default_driver)
            self.audio_input_combobox = customtkinter.CTkComboBox(master=self,
                                                                  values=self.audio_driver_names,
                                                                  command=self.audio_driver_dropdown_callback,
                                                                  variable=self.audio_input_combobox_var)
            self.audio_input_combobox.grid(
                row=0, column=1, padx=10, pady=10, sticky='W')

        if show_device_selection:
            # device selection
            audio_input_label = customtkinter.CTkLabel(
                master=self, text=f'{device_type} device: ')
            audio_input_label.grid(
                row=1, column=0, padx=10, pady=10, sticky='W')

            self.audio_devices = self.get_audio_devices(
                self.driver_to_id(self.default_driver))
            self.filtered_devices = self.audio_devices
            if self.device_type == 'input':
                self.filtered_devices = list(filter(
                    lambda device: device['max_input_channels'] > 0, self.audio_devices))
            elif self.device_type == 'output':
                self.filtered_devices = list(filter(
                    lambda device: device['max_output_channels'] > 0, self.audio_devices))
            self.filtered_audio_device_names = list(
                map(lambda device: device['name'], self.filtered_devices))
            self.filtered_audio_device_names.insert(0, 'Default')
            # If the device name in settings can be found, use the settings
            device_setting = ''
            if device_type == 'input':
                device_setting = settings.get_settings('input_device')
            elif device_type == 'output':
                device_setting = settings.get_settings(f'output_device_{self.index}')
            default_device = 'Default'
            print(
                f'Looking for \'{device_setting}\' in {self.filtered_audio_device_names}.')
            if device_setting in self.filtered_audio_device_names:
                print("found")
                default_device = device_setting
            self.audio_input_combobox_var = customtkinter.StringVar(
                value=default_device)
            self.audio_input_combobox = customtkinter.CTkComboBox(master=self,
                                                                  values=self.filtered_audio_device_names,
                                                                  command=self.audio_input_dropdown_callback,
                                                                  variable=self.audio_input_combobox_var)
            self.audio_input_combobox.grid(
                row=1, column=1, padx=10, pady=10, sticky='W')

        if self.device_type == 'input' and show_mic_meter:
            label_mic = customtkinter.CTkLabel(
                master=self, text='Mic activity: ')
            label_mic.grid(row=2, column=0, padx=10, pady=10, sticky='W')
            self.progressbar = customtkinter.CTkProgressBar(
                master=self, width=100)
            self.progressbar.grid(
                row=3, column=0, padx=10, pady=10, sticky='W')
            self.mic = Microphone()
            self.mic.start_thread(device=get_command())
            self.update_mic_meter_thread = Thread(target=self.update_mic_meter_loop, daemon=True)
            mic_meters.append(self)


    def update_mic_meter_loop(self):
        while True:
            self.update_mic_meter()

    def update_mic_meter(self):
        self.progressbar.set(self.mic.volume)
        time.sleep(0.05)

    def listen_to_mic(self):
        self._subtitle_mic_stream = sd.InputStream(
            callback=self.update_sound, device=self.get_command(self.index))
        with self._subtitle_mic_stream:
            sd.sleep(10000000)

    def audio_input_dropdown_callback(self, choice):
        if self.device_type == 'input':
            settings.save_settings('input_device', choice)
        elif self.device_type == 'output':
            settings.save_settings(f'output_device_{self.index}', choice)
        if choice == 'Default':
            device_id = None
        else:
            print(choice)
            device = next(
                device for device in self.filtered_devices if device['name'] == choice)
            device_id = device['index']
            print(device)
        print(f'Setting {self.device_type} audio device id to: {device_id}')
        self.set_command(device_id, self.index)
        if self.device_type == 'input':
            print(f"restarted micrometer with device id: {device_id}")
            self.restart_mic_meter()

    @staticmethod
    def restart_mic_meter():
        global mic_meters
        for mic_meter in mic_meters:
            print(mic_meter.get_command())
            mic_meter.mic.start_thread(device=mic_meter.get_command())

    def audio_driver_dropdown_callback(self, choice):
        print(choice)
        driver_idx = 0
        for idx, driver in enumerate(self.audio_drivers):
            if driver['name'] == choice:
                driver_idx = idx
                if self.device_type == 'input':
                    settings.save_settings('input_audio_driver', choice)
                elif self.device_type == 'output':
                    settings.save_settings(f'output_audio_driver_{self.index}', choice)
        print(f'Selected driver with idx: {driver_idx}')
        self.audio_devices = self.get_audio_devices(hostapi=driver_idx)
        self.filtered_devices = self.audio_devices
        if self.device_type == 'input':
            self.filtered_devices = list(filter(
                lambda device: device['max_input_channels'] > 0, self.audio_devices))
        elif self.device_type == 'output':
            self.filtered_devices = list(filter(
                lambda device: device['max_output_channels'] > 0, self.audio_devices))
        self.filtered_audio_device_names = list(
            map(lambda device: device['name'], self.filtered_devices))
        self.filtered_audio_device_names.insert(0, 'Default')
        self.audio_input_combobox_var = customtkinter.StringVar(
            value='Default')
        self.audio_input_combobox.configure(values=self.filtered_audio_device_names,
                                            variable=self.audio_input_combobox_var)
        print(self.filtered_audio_device_names)
        device_id = None
        print(f'Setting {self.device_type} audio device id to: {device_id}')
        self.set_command(device_id, self.index)
        if self.device_type == 'input':
            print(f"restarted micrometer with device id: {device_id}")
            self.restart_mic_meter()

    @staticmethod
    def get_audio_drivers():
        global hostapis
        return hostapis

    @staticmethod
    def get_audio_devices(hostapi=0):
        global audio_devices
        devices = list(filter(lambda device: device['hostapi'] == hostapi, audio_devices))
        return devices

    def update_sound(self, indata, _outdata, _frames, _time):
        self.audio_level = np.linalg.norm(indata)/10

    @staticmethod
    def driver_to_id(driver_name):
        global hostapis
        for idx, driver in enumerate(hostapis):
            if driver['name'] == driver_name:
                return idx


class SubtitlesFrame(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.subtitle_overlay: Optional['SubtitleOverlay'] = None
        self.position_label = customtkinter.CTkLabel(
            master=self, text='Subtitle position')
        self.position_label.grid(row=0, column=0, padx=10, pady=10, sticky='W')
        self.sub_pos_x = 0.5
        self.sub_pos_y = 0.8

        x_slider = customtkinter.CTkSlider(
            master=self, from_=0, to=100, command=self.slider_event_x, variable=customtkinter.DoubleVar(self, self.sub_pos_x*100))
        x_slider.grid(row=0, column=1, padx=10, pady=10, sticky='W')
        y_slider = customtkinter.CTkSlider(
            master=self, from_=0, to=100, command=self.slider_event_y, variable=customtkinter.DoubleVar(self, self.sub_pos_y*100))
        y_slider.grid(row=0, column=2, padx=10, pady=10, sticky='W')

        self.sub_alpha = 0.8
        self.alpha_label = customtkinter.CTkLabel(self, text='Subtitle alpha')
        self.alpha_label.grid(row=1, column=0, padx=10, pady=10, sticky='W')
        alpha_slider = customtkinter.CTkSlider(
            self, from_=0, to=100, command=self.slider_event_alpha, variable=customtkinter.DoubleVar(self, self.sub_alpha*100))
        alpha_slider.grid(row=1, column=1, padx=10, pady=10, sticky='W')

        self.toggle_overlay_button = customtkinter.CTkButton(
            self, text="start overlay", command=self.toggle_subtitle_button_callback)
        self.toggle_overlay_button.grid(row=5, column=0, padx=10, pady=10, sticky='W')

        self.front = ["Arial", 45]

    def slider_event_alpha(self, value):
        self.sub_alpha = value/100
        if self.subtitle_overlay is not None:
            self.subtitle_overlay.attributes('-alpha', self.sub_alpha)

    def slider_event_x(self, value):
        self.sub_pos_x = value/100
        self.move_text(self.sub_pos_x, self.sub_pos_y)

    def slider_event_y(self, value):
        self.sub_pos_y = value/100
        self.move_text(self.sub_pos_x, self.sub_pos_y)

    def toggle_subtitle_button_callback(self):
        if self.subtitle_overlay is None or not self.subtitle_overlay.winfo_exists():
            # create window if its None or destroyed
            self._open_subtitle_overlay()
            self.toggle_overlay_button.configure(
                text="close overlay", fg_color='#fc7b5b')
        else:
            self._stop_subtitle_overlay()
            self.toggle_overlay_button.configure(
                text="start overlay", fg_color='grey')

    def _open_subtitle_overlay(self):
        if self.subtitle_overlay is None or not self.subtitle_overlay.winfo_exists():
            # create window if its None or destroyed
            self.subtitle_overlay = SubtitleOverlay(self)
            SUB.text_change_eventhandlers.append(self.update_text)
            SUB.start()
        else:
            self.subtitle_overlay.focus()  # if window exists focus it

    def _stop_subtitle_overlay(self):
        if not (self.subtitle_overlay is None or not self.subtitle_overlay.winfo_exists()):
            SUB.text_change_eventhandlers.remove(self.update_text)
            self.subtitle_overlay.destroy()
            SUB.stop()
            self.subtitle_overlay = None

    def update_text(self, text: str):
        if self.subtitle_overlay is not None:
            label = self.subtitle_overlay.label
            self.front[1] = 45
            text = text.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').replace('* ', '*\n')
            while text.endswith('\n'):
                text = text.removesuffix('\n')
            label.configure(text=text, font=tuple(self.front))
            label.place(x=0, y=0)
            label.update_idletasks()

            while label.winfo_width() > self.subtitle_overlay.winfo_width() or label.winfo_height() > self.subtitle_overlay.winfo_height():
                self.front[1] -= 1
                label.configure(font=tuple(self.front))
                label.update_idletasks()

            if self.sub_pos_y > 0.5:
                i = 0
                while label.winfo_y() + label.winfo_height() > self.subtitle_overlay.winfo_height():
                    i -= 1
                    label.place(y=i)
                    label.update_idletasks()
            else:
                i = 0
                while label.winfo_y() < 0:
                    i += 1
                    label.place(y=i)
                    label.update_idletasks()

            if self.sub_pos_x > 0.5:
                i = 0
                while label.winfo_x() + label.winfo_width() > self.subtitle_overlay.winfo_width():
                    i -= 1
                    label.place(x=i)
                    label.update_idletasks()
            else:
                i = 0
                while label.winfo_x() < 0:
                    i += 1
                    label.place(x=i)
                    label.update_idletasks()

    def move_text(self, x, y):
        if self.subtitle_overlay is not None:
            self.subtitle_overlay.label.place(relx=x, rely=y)


class SubtitleOverlay(customtkinter.CTkToplevel):
    def __init__(self, sub_frame: SubtitlesFrame):
        super().__init__()
        self.geometry("1920x1080+0+0")
        self.title("app")
        self.resizable(True, True)

        self.attributes("-topmost", True)
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', sub_frame.sub_alpha)
        self.state('zoomed')

        self.wm_attributes('-transparentcolor', 'black')
        self.configure(fg_color='black')
        self.label = customtkinter.CTkLabel(
            master=self, text='This is a long long default text for testing. You can change the position and alpha by yourself.'.replace('. ', '.\n').removesuffix('\n'),
            fg_color='#111111', text_color="white", font=tuple(sub_frame.front))
        self.label.place(relx=sub_frame.sub_pos_x, rely=sub_frame.sub_pos_y, anchor='center')
        self.protocol("WM_DELETE_WINDOW", sub_frame.toggle_subtitle_button_callback)


class OptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, enable_input_language=True, **kwargs):
        super().__init__(master, **kwargs)
        self.speaker_names = STTS.get_speaker_names()
        self.default_speaker = self.speaker_names[0]
        self.current_speaker = self.default_speaker

        self.current_styles = STTS.get_speaker_styles(self.current_speaker)
        self.selected_style = self.current_styles[0]
        STTS.speaker_id = self.selected_style['id']

        if enable_input_language:
            self.default_input_language = "English"
            self.input_language = list(dict.language_dict.keys())

            label_Input = customtkinter.CTkLabel(
                master=self, text='Input Language: ')
            label_Input.pack(padx=20, pady=10)
            self.input_language_combobox_var = customtkinter.StringVar(
                value=self.default_input_language)
            input_language_combobox = customtkinter.CTkComboBox(master=self,
                                                                values=self.input_language,
                                                                command=self.input_dropdown_callback,
                                                                variable=self.input_language_combobox_var)
            input_language_combobox.pack(padx=20, pady=0,)
            option_frame_list.append(self)

        label_Input = customtkinter.CTkLabel(
            master=self, text='Speaker: ')
        label_Input.pack(padx=20, pady=10)
        self.speaker_combobox_var = customtkinter.StringVar(
            value=self.default_speaker)
        STTS.voice_name = self.default_speaker
        self.speaker_combobox = customtkinter.CTkComboBox(master=self,
                                                          values=self.speaker_names,
                                                          command=self.voice_dropdown_callback,
                                                          variable=self.speaker_combobox_var)
        self.speaker_combobox.pack(padx=20, pady=0)

        label_Input = customtkinter.CTkLabel(
            master=self, text='Style: ')
        label_Input.pack(padx=20, pady=10)
        self.style_combobox_var = customtkinter.StringVar(
            value=self.selected_style['name'])
        STTS.speaker_id = self.selected_style['id']
        self.style_combobox = customtkinter.CTkComboBox(master=self,
                                                        values=list(
                                                            map(lambda style: style['name'], self.current_styles)),
                                                        command=self.style_dropdown_callback,
                                                        variable=self.style_combobox_var)
        self.style_combobox.pack(padx=20, pady=0)

        self.audio_device_selection = AudiodeviceSelection(
            master=self,
            set_command=self.input_device_index_update_callback,
            get_command=self.input_device_index_get_callback,
            device_type='input', show_driver_selection=False, show_device_selection=False)
        self.audio_device_selection.pack(padx=20, pady=10)

        option_menu_list.append(self)

    def refresh_speaker(self):
        self.speaker_names = STTS.get_speaker_names()
        self.default_speaker = self.speaker_names[0]
        self.current_speaker = self.default_speaker

        self.current_styles = STTS.get_speaker_styles(self.current_speaker)
        self.selected_style = self.current_styles[0]
        STTS.speaker_id = self.selected_style['id']

        self.speaker_combobox_var.set(self.default_speaker)
        STTS.voice_name = self.default_speaker
        self.speaker_combobox.configure(values=self.speaker_names)

        self.style_combobox_var.set(self.selected_style['name'])
        self.style_combobox.configure(values=list(map(lambda style: style['name'], self.current_styles)))


    @staticmethod
    def input_device_index_update_callback(value, _=None):
        STTS.input_device_id = value

    @staticmethod
    def input_device_index_get_callback(_=None):
        return STTS.input_device_id

    @staticmethod
    def input_dropdown_callback(choice):
        global option_frame_list
        STTS.change_input_language(choice)
        for i in option_frame_list:
            i.input_language_combobox_var.set(choice)

    def voice_dropdown_callback(self, choice):
        self.current_speaker = choice
        self.current_styles = STTS.get_speaker_styles(self.current_speaker)
        self.style_combobox.configure(values=list(
            map(lambda style: style['name'], self.current_styles)))
        self.selected_style = self.current_styles[0]
        self.style_combobox_var = customtkinter.StringVar(
            value=self.selected_style['name'])
        self.style_combobox.configure(variable=self.style_combobox_var)
        STTS.speaker_id = self.selected_style['id']
        print(f'Changed speaker ID to: {STTS.speaker_id}')

    def style_dropdown_callback(self, choice):
        STTS.speaker_id = next(
            style['id'] for style in self.current_styles if choice == style['name'])
        print(f'Changed speaker ID to: {STTS.speaker_id}')


class StreamFrame(customtkinter.CTkFrame):
    def __init__(self, master, stream_type='youtube', **kwargs):
        super().__init__(master, **kwargs)
        if stream_type == 'youtube':
            label_youtube_video_id = customtkinter.CTkLabel(
                master=self, text='Youtube video id \n (example: Sdx3kCr8DvQ)')
            label_youtube_video_id.pack(padx=20, pady=5)
            self.youtube_video_id_var = customtkinter.StringVar(
                self, streamChat.youtube_video_id)
            self.youtube_video_id_var.trace_add(
                'write', self.update_youtube_video_id)
            self.youtube_stream_id_input = customtkinter.CTkEntry(
                master=self, textvariable=self.youtube_video_id_var)
            self.youtube_stream_id_input.pack(padx=20, pady=5)

            self.toggle_start_Button = customtkinter.CTkButton(master=self,
                                                               text="Start fetching chat",
                                                               command=self.toggle_start_button_callback_youtube,
                                                               fg_color='grey'
                                                               )
            self.toggle_start_Button.pack(padx=20, pady=10)

        elif stream_type == 'twitch':
            label_twitch_access_token = customtkinter.CTkLabel(
                master=self, text='Twitch access token: \n (get from twitchtokengenerator.com)')
            label_twitch_access_token.pack(padx=20, pady=0)
            self.twitch_access_token_var = customtkinter.StringVar(
                self, streamChat.twitch_access_token)
            self.twitch_access_token_var.trace_add(
                'write', self.update_twitch_token)
            self.youtube_stream_id_input = customtkinter.CTkEntry(
                master=self, textvariable=self.twitch_access_token_var)
            self.youtube_stream_id_input.pack(padx=20, pady=0)

            label_twitch_channel_name = customtkinter.CTkLabel(
                master=self, text='Twitch channel name: ')
            label_twitch_channel_name.pack(padx=20, pady=0)
            self.twitch_channel_name_var = customtkinter.StringVar(
                self, streamChat.twitch_channel_name)
            self.twitch_channel_name_var.trace_add(
                'write', self.update_twitch_chanel_name)
            self.youtube_stream_id_input = customtkinter.CTkEntry(
                master=self, textvariable=self.twitch_channel_name_var)
            self.youtube_stream_id_input.pack(padx=20, pady=0)

            self.toggle_start_Button_twitch = customtkinter.CTkButton(master=self,
                                                                      text="Start fetching chat",
                                                                      command=self.toggle_start_button_callback_twitch,
                                                                      fg_color='grey'
                                                                      )
            self.toggle_start_Button_twitch.pack(padx=20, pady=10)

    @staticmethod
    def start_fetch_youtube():
        streamChat.read_chat_youtube()

    @staticmethod
    def stop_fetch_youtube():
        streamChat.stop_read_chat_youtube()

    def toggle_start_button_callback_youtube(self):
        if streamChat.read_chat_youtube_thread_running:
            self.stop_fetch_youtube()
            self.toggle_start_Button.configure(
                text="Start fetching chat", fg_color='grey')
        else:
            self.start_fetch_youtube()
            if streamChat.read_chat_youtube_thread_running:
                self.toggle_start_Button.configure(
                    text="Stop fetching chat", fg_color='#fc7b5b')

    def update_youtube_video_id(self, _1, _2, _3):
        streamChat.youtube_video_id = self.youtube_video_id_var.get()
        STTS.save_config('youtube_video_id', streamChat.youtube_video_id)

    @staticmethod
    def start_fetch_twitch():
        streamChat.read_chat_twitch()

    @staticmethod
    def stop_fetch_twitch():
        streamChat.stop_read_chat_twitch()

    def toggle_start_button_callback_twitch(self):
        if streamChat.read_chat_twitch_thread_running:
            streamChat.stop_read_chat_twitch()
            if not streamChat.read_chat_twitch_thread_running:
                self.toggle_start_Button_twitch.configure(
                    text="Start fetching chat", fg_color='grey')
        else:
            streamChat.read_chat_twitch()
            if streamChat.read_chat_twitch_thread_running:
                self.toggle_start_Button_twitch.configure(
                    text="Stop fetching chat", fg_color='#fc7b5b')

    def update_twitch_token(self, _1, _2, _3):
        streamChat.twitch_access_token = self.twitch_access_token_var.get()
        STTS.save_config('twitch_access_token', streamChat.twitch_access_token)

    def update_twitch_chanel_name(self, _1, _2, _3):
        streamChat.twitch_channel_name = self.twitch_channel_name_var.get()
        STTS.save_config('twitch_channel_name', streamChat.twitch_channel_name)


class SettingsFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master,  **kwargs):
        super().__init__(master, **kwargs)
        mic_mode_label = customtkinter.CTkLabel(
            master=self, text='Microphone mode: ')
        mic_mode_label.grid(row=0, column=0, padx=10,
                            pady=10, sticky='W')
        default_mic_mode = 'open mic'
        mic_mode_setting = settings.get_settings('mic_mode')
        if mic_mode_setting in ['open mic', 'push to talk']:
            default_mic_mode = mic_mode_setting
        STTS.mic_mode = default_mic_mode
        self.mic_mode_combobox_var = customtkinter.StringVar(
            value=default_mic_mode)
        self.mic_mode_combobox = customtkinter.CTkComboBox(master=self,
                                                           values=[
                                                               'open mic', 'push to talk'],
                                                           command=self.mic_mode_dropdown_callback,
                                                           variable=self.mic_mode_combobox_var)
        self.mic_mode_combobox.grid(
            row=0, column=1, padx=10, pady=10, sticky='W')
        default_push_to_talk_key = '5'
        push_to_talk_key_setting = settings.get_settings('push_to_talk_key')
        if push_to_talk_key_setting:
            default_push_to_talk_key = push_to_talk_key_setting
        self.mic_key_label = customtkinter.CTkLabel(
            master=self, text=f'push to talk key: {default_push_to_talk_key}')
        self.mic_key_label.grid(row=1, column=0,
                                padx=10, pady=10, sticky='W')
        self.change_mic_key_Button = customtkinter.CTkButton(master=self,
                                                             text="change key",
                                                             command=self.change_push_to_talk_key,
                                                             fg_color='grey'
                                                             )
        self.change_mic_key_Button.grid(
            row=1, column=1, padx=10, pady=10, sticky='W')


        self.audio_device_selection = AudiodeviceSelection(
            master=self, set_command=self.input_device_index_update_callback,
            get_command=self.input_device_index_get_callback, device_type='input')
        self.audio_device_selection.grid(
            row=3, column=0, padx=10, pady=10, sticky='NW', rowspan=1, columnspan=2)
        self.audio_device_selection = AudiodeviceSelection(
            master=self, set_command=self.output_device_index_update_callback,
            get_command=self.output_device_index_get_callback, device_type='output', index=0)
        self.audio_device_selection.grid(
            row=3, column=1, padx=10, pady=10, sticky='NW', rowspan=1, columnspan=3)
        self.audio_device_selection = AudiodeviceSelection(
            master=self, set_command=self.output_device_index_update_callback,
            get_command=self.output_device_index_get_callback, device_type='output', index=1)
        self.audio_device_selection.grid(
            row=4, column=0, padx=10, pady=10, sticky='NW', rowspan=1, columnspan=3)


        self.use_voicevox_var = customtkinter.BooleanVar(self, STTS.use_voicevox)
        use_voicevox_checkbox = customtkinter.CTkCheckBox(self, text='Use voicevox',
                                                          command=self.set_use_voicevox_var,
                                                          variable=self.use_voicevox_var, onvalue=True, offvalue=False)
        use_voicevox_checkbox.grid(row=5, column=0, padx=10, pady=10, sticky='W')
        self.use_cloud_voicevox_var = customtkinter.BooleanVar(self, STTS.use_cloud_voicevox)
        use_cloud_voicevox_checkbox = customtkinter.CTkCheckBox(master=self, text="Use voicevox on cloud (api key optional)",
                                                                command=self.set_use_cloud_voicevox_var,
                                                                variable=self.use_cloud_voicevox_var, onvalue=True, offvalue=False)
        use_cloud_voicevox_checkbox.grid(row=6, column=0, padx=10, pady=10, sticky='W')
        self.voicevox_api_key_var = customtkinter.StringVar(self, STTS.voicevox_api_key)
        self.voicevox_api_key_var.trace_add('write', self.update_voicevox_api_key)
        self.voicevox_api_key_input = customtkinter.CTkEntry(master=self, textvariable=self.voicevox_api_key_var)
        self.voicevox_api_key_input.grid(row=6, column=1, padx=10, pady=10, sticky='W')

        self.local_voicevox_url_label = customtkinter.CTkLabel(self, text='Voicevox engine url')
        self.local_voicevox_url_label.grid(row=7, column=0, padx=10, pady=10, sticky='W')
        self.local_voicevox_url_var = customtkinter.StringVar(self, STTS.VOICE_VOX_URL_LOCAL)
        self.local_voicevox_url_var.trace_add('write', self.update_voicevox_local_url)
        self.local_voicevox_url_entry = customtkinter.CTkEntry(master=self, textvariable=self.local_voicevox_url_var)
        self.local_voicevox_url_entry.grid(row=7, column=1, padx=10, pady=10, sticky='W')

        self.local_voicevox_reconnect_button = customtkinter.CTkButton(master=self, text=f'Connect: {STTS.voicevox_server_started}',
                                                                       command=self.connect_voicevox_engine)
        self.local_voicevox_reconnect_button.grid(row=8, column=0, padx=10, pady=10, sticky='W')

        self.use_elevenlab_var = customtkinter.BooleanVar(self, STTS.use_elevenlab)
        use_elevenlab_checkbox = customtkinter.CTkCheckBox(master=self, text="Use elevenlab on cloud (api key required)", command=self.set_use_elevenlab_var,
                                                           variable=self.use_elevenlab_var, onvalue=True, offvalue=False)
        use_elevenlab_checkbox.grid(row=9, column=0, padx=10, pady=10, sticky='W')
        self.elevenlab_api_key_var = customtkinter.StringVar(self, STTS.voicevox_api_key)
        self.elevenlab_api_key_var.trace_add('write', self.update_elevenlab_api_key)
        self.elevenlab_api_key_input = customtkinter.CTkEntry(master=self, textvariable=self.elevenlab_api_key_var)
        self.elevenlab_api_key_input.grid(row=9, column=1, padx=10, pady=10, sticky='W')

        with open("elevenlabVoices.json", "r") as json_file:
            elevenlab_voice_response = json.load(json_file)
            self.elevenlab_voice_list = list(map(lambda voice: {
                "name": voice['name'], "voice_id": voice['voice_id']},  elevenlab_voice_response['voices']))
            self.elevenlab_voice_list_names = list(
                map(lambda voice: voice['name'],  elevenlab_voice_response['voices']))

        default_voice = "Elli"
        elevenlab_voice_setting = settings.get_settings("elevenlab_voice_name")

        if elevenlab_voice_setting != '':
            default_voice = elevenlab_voice_setting
        self.elevenlab_voice_combobox_var = customtkinter.StringVar(value=default_voice)
        self.audio_input_combobox = customtkinter.CTkComboBox(master=self,
                                                              values=self.elevenlab_voice_list_names,
                                                              command=self.elevenlab_voice_dropdown_callback,
                                                              variable=self.elevenlab_voice_combobox_var)
        self.audio_input_combobox.grid(row=10, column=0, padx=10, pady=10, sticky='W')


        self.vall_e_x_url_label = customtkinter.CTkLabel(self, text='Vall-e-x url')
        self.vall_e_x_url_label.grid(row=11, column=0, padx=10, pady=10, sticky='W')
        self.vall_e_x_url_var = customtkinter.StringVar(self, STTS.VALL_E_X_URL)
        self.vall_e_x_url_var.trace_add('write', self.update_vall_e_x_url)
        self.vall_e_x_url_entry = customtkinter.CTkEntry(self, textvariable=self.vall_e_x_url_var)
        self.vall_e_x_url_entry.grid(row=11, column=1, padx=10, pady=10, sticky='W')


        default = False
        setting = settings.get_settings('use_ingame_push_to_talk')
        if setting != '':
            default = setting
        STTS.use_ingame_push_to_talk_key = default
        self.use_ingame_push_to_talk_key_var = customtkinter.BooleanVar(self, STTS.use_ingame_push_to_talk_key)
        default = 'f'
        setting = settings.get_settings('ingame_push_to_talk_key')
        if setting != '':
            default = setting
        STTS.ingame_push_to_talk_key = default
        self.ingame_push_to_talk_key_checkbox = customtkinter.CTkCheckBox(master=self,
                                                                          text=f'In-game push to talk key: {STTS.ingame_push_to_talk_key}',
                                                                          command=self.set_use_ingame_push_to_talk_key_var,
                                                                          variable=self.use_ingame_push_to_talk_key_var,
                                                                          onvalue=True, offvalue=False)
        self.ingame_push_to_talk_key_checkbox.grid(row=13, column=0, padx=10, pady=10, sticky='W')

        self.ingame_push_to_talk_key_Button = customtkinter.CTkButton(master=self,
                                                                      text="change key",
                                                                      command=self.change_ingame_push_to_talk_key,
                                                                      fg_color='grey')
        self.ingame_push_to_talk_key_Button.grid(row=13, column=1, padx=10, pady=10, sticky='W')

        self.text_ui_url_label = customtkinter.CTkLabel(self, text='text-ui url')
        self.text_ui_url_label.grid(row=14, column=0, padx=10, pady=10, sticky='W')
        self.text_ui_url_var = customtkinter.StringVar(self, chatbot.HOST)
        self.text_ui_url_var.trace_add('write', self.update_text_ui_url)
        self.text_ui_url_entry = customtkinter.CTkEntry(self, textvariable=self.text_ui_url_var)
        self.text_ui_url_entry.grid(row=14, column=1, padx=10, pady=10, sticky='W')

    def connect_voicevox_engine(self):
        STTS.connect_voicevox_server()
        self.local_voicevox_reconnect_button.configure(text=f'Connect: {STTS.voicevox_server_started}')
        if STTS.voicevox_server_started:
            for i in option_menu_list:
                i.refresh_speaker()

    @staticmethod
    def input_device_index_update_callback(value, _=None):
        STTS.input_device_id = value

    @staticmethod
    def input_device_index_get_callback(_=None):
        return STTS.input_device_id

    @staticmethod
    def output_device_index_update_callback(value, index):
        STTS.output_device_id[index] = value

    @staticmethod
    def output_device_index_get_callback(index):
        return STTS.output_device_id[index]

    @staticmethod
    def mic_mode_dropdown_callback(choice):
        STTS.mic_mode = choice
        settings.save_settings('mic_mode', choice)

    def set_use_voicevox_var(self):
        print(f'use_voicevox set to {self.use_voicevox_var.get()}')
        STTS.use_voicevox = self.use_voicevox_var.get()
        STTS.save_config('use_voicevox', STTS.use_voicevox)

    def set_use_cloud_voicevox_var(self):
        print(f'use_cloud_voicevox set to {self.use_cloud_voicevox_var.get()}')
        STTS.use_cloud_voicevox = self.use_cloud_voicevox_var.get()
        STTS.save_config('use_cloud_voicevox', STTS.use_cloud_voicevox)

    def update_text_ui_url(self, _1, _2, _3):
        chatbot.HOST = self.text_ui_url_var.get()
        STTS.save_config('text_ui_url', chatbot.HOST)

    def update_voicevox_api_key(self, _1, _2, _3):
        STTS.voicevox_api_key = self.voicevox_api_key_var.get()
        STTS.save_config('voicevox_api_key', STTS.voicevox_api_key)

    def update_voicevox_local_url(self, _1, _2, _3):
        STTS.VOICE_VOX_URL_LOCAL = self.local_voicevox_url_var.get()
        STTS.save_config('voicevox_local_url', STTS.VOICE_VOX_URL_LOCAL)

    def set_use_elevenlab_var(self):
        print(f'use_elevenlab set to {self.use_cloud_voicevox_var.get()}')
        STTS.use_elevenlab = self.use_elevenlab_var.get()
        STTS.save_config('use_elevenlab', STTS.use_elevenlab)

    def update_elevenlab_api_key(self, _1, _2, _3):
        STTS.elevenlab_api_key = self.elevenlab_api_key_var.get()
        STTS.save_config('elevenlab_api_key', STTS.elevenlab_api_key)

    def update_vall_e_x_url(self, _1, _2, _3):
        STTS.VALL_E_X_URL = self.vall_e_x_url_var.get()
        STTS.save_config('vall_e_x_url', STTS.VALL_E_X_URL)

    def change_push_to_talk_key(self):
        thread = Thread(target=self.listen_for_key)
        thread.start()

    def change_ingame_push_to_talk_key(self):
        thread = Thread(target=self.listen_for_key_ingame)
        thread.start()

    def set_use_ingame_push_to_talk_key_var(self):
        print(
            f'use_ingame_push_to_talk_key set to {self.use_ingame_push_to_talk_key_var.get()}')
        STTS.use_ingame_push_to_talk_key = self.use_ingame_push_to_talk_key_var.get()
        settings.save_settings("use_ingame_push_to_talk",
                               STTS.use_ingame_push_to_talk_key)

    def listen_for_key(self):
        self.mic_key_label.configure(text='listening to keypress...')
        self.change_mic_key_Button.configure(fg_color='#fc7b5b')
        key = keyboard.read_key()
        STTS.PUSH_TO_RECORD_KEY = key
        settings.save_settings('push_to_talk_key', value=key)
        self.mic_key_label.configure(
            text=f'push to talk key: {STTS.PUSH_TO_RECORD_KEY}')
        self.change_mic_key_Button.configure(fg_color='grey')

    def listen_for_key_ingame(self):
        self.ingame_push_to_talk_key_checkbox.configure(
            text='listening to keypress...')
        self.ingame_push_to_talk_key_Button.configure(fg_color='#fc7b5b')
        key = keyboard.read_key()
        STTS.ingame_push_to_talk_key = key
        settings.save_settings("ingame_push_to_talk_key", key)
        self.ingame_push_to_talk_key_checkbox.configure(
            text=f'In-game push to talk key: {STTS.ingame_push_to_talk_key}')
        self.ingame_push_to_talk_key_Button.configure(fg_color='grey')

    def elevenlab_voice_dropdown_callback(self, choice):
        for voice in self.elevenlab_voice_list:
            if voice['name'] == choice:
                settings.save_settings("elevenlab_voice_name", choice)
                STTS.elevenlab_voice_id = voice['voice_id']


class Page(customtkinter.CTkFrame):
    def __init__(self, *args, **kwargs):
        customtkinter.CTkFrame.__init__(self, *args, **kwargs)

    def show(self):
        self.lift()


class AudioInputPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        console = ConsoleFrame(master=self, width=500, corner_radius=8)
        console.grid(row=0, column=1, padx=20, pady=20,
                     sticky="nswe")
        options = OptionsFrame(master=self)
        options.grid(row=0, column=2, padx=20,
                     pady=20, sticky="nswe")


class TextInputPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        textbox = TextBoxFrame(master=self, width=500, corner_radius=8)
        textbox.grid(row=0, column=1, padx=20, pady=20,
                     sticky="nswe")
        options = OptionsFrame(master=self)
        options.grid(row=0, column=2, padx=20,
                     pady=20, sticky="nswe")


class SubtitlesPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        subtitles_frame = SubtitlesFrame(
            master=self, width=500, corner_radius=8)
        subtitles_frame.pack(padx=0, pady=0)


class ChatPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        chat_frame = ChatFrame(
            master=self, width=500, corner_radius=8)
        chat_frame.grid(row=0, column=1, padx=20, pady=20,
                        sticky="nswe")
        options = OptionsFrame(master=self)
        options.grid(row=0, column=2, padx=20,
                     pady=20, sticky="nswe")


class StreamPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        stream_frame = StreamFrame(
            master=self, stream_type='youtube',  width=500, corner_radius=8)
        stream_frame.grid(row=0, column=0, padx=20, pady=20,
                          sticky="nswe")
        stream_frame = StreamFrame(
            master=self, stream_type='twitch',  width=500, corner_radius=8)
        stream_frame.grid(row=0, column=1, padx=20, pady=20,
                          sticky="nswe")

        self.chat_textbox = customtkinter.CTkTextbox(
            self, width=200, height=200)
        self.chat_textbox.grid(row=1, column=0, padx=20, pady=20, columnspan=2,
                               sticky="nswe")
        streamChat.logging_eventhandlers.append(self.log_message_on_console)

    def log_message_on_console(self, message_text):
        # insert at line 0 character 0
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert(customtkinter.INSERT, message_text+'\n')
        self.chat_textbox.configure(state="disabled")
        self.chat_textbox.see("end")


class SettingsPage(Page):
    def __init__(self, *args, **kwargs):
        Page.__init__(self, *args, **kwargs)
        settings_frame = SettingsFrame(
            master=self, width=620, height=440,  corner_radius=8)
        settings_frame.grid(row=0, column=0, padx=0, pady=0,
                            sticky="nswe")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("850x500")
        self.title("Chat bot console")
        self.resizable(False, False)
        self.iconbitmap('./icon.ico', './icon.ico')
        self.configure(background='#fafafa')

        sidebar = SidebarFrame(master=self, width=100)
        sidebar.grid(row=0, column=0, padx=20,
                     pady=20, sticky="nswe")

        audioInputPage = AudioInputPage(self)
        textInputPage = TextInputPage(self)
        settingsPage = SettingsPage(self)
        subtitlesPage = SubtitlesPage(self)
        streamPage = StreamPage(self)
        chatPage = ChatPage(self)
        container = customtkinter.CTkFrame(
            self, width=700, height=700, bg_color='#fafafa')
        container.grid(row=0, column=1, padx=20,
                       pady=20, sticky="nswe")

        audioInputPage.place(in_=container, x=0, y=0)
        textInputPage.place(in_=container, x=0, y=0)
        subtitlesPage.place(in_=container, x=0, y=0)
        chatPage.place(in_=container, x=0, y=0)
        settingsPage.place(in_=container, x=0, y=0)
        streamPage.place(in_=container, x=0, y=0)

        chatPage.show()
        global pageChange_eventhandlers

        def showPage():
            global current_page
            if current_page == Pages.AUDIO_INPUT:
                container.lift()
                audioInputPage.show()
            elif current_page == Pages.TEXT_INPUT:
                container.lift()
                textInputPage.show()
            elif current_page == Pages.SUBTITLE:
                container.lift()
                subtitlesPage.show()
            elif current_page == Pages.SETTINGS:
                container.lift()
                settingsPage.show()
            elif current_page == Pages.STREAM:
                container.lift()
                streamPage.show()
            elif current_page == Pages.CHAT:
                container.lift()
                chatPage.show()
        pageChange_eventhandlers.append(showPage)


def option_menu_callback(choice):
    print("option menu dropdown clicked:", choice)


def print_sound(indata, _outdata, _frames, _time, _status):
    global audio_level
    audio_level = np.linalg.norm(indata) / 10


def listen_to_mic():
    with sd.Stream(callback=print_sound):
        while True:
            sd.sleep(10000000)


def initialize_audio_devices():
    global hostapis
    hostapis = sd.query_hostapis()
    global audio_devices
    audio_devices = sd.query_devices()


hostapis: tuple
audio_devices: Optional[list] = None
thread = Thread(target=listen_to_mic, daemon=True)
thread.start()


print("Initializing stt model...")
STTS.initialize_model()
print("loading Audio devices: ")
initialize_audio_devices()
print("loading config... ")
STTS.load_config()
print("loading settings... ")
settings.load_settings()

app = App()

STTS.is_show_voicevox_connect_warn = False
for i in mic_meters:
    i.update_mic_meter_thread.start()

app.mainloop()

STTS.auto_recording = False
chatbot.is_random_dialog_running = False
streamChat.read_chat_youtube_thread_running = False
SUB.is_running = False