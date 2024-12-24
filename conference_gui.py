import tkinter as tk
from tkinter import simpledialog, scrolledtext, BOTH
import asyncio

import cv2
from PIL import Image, ImageTk, ImageGrab

from conf_client import ConferenceClient
from config import *

import datetime

from util import resize_image_to_fit_screen

ON_COLOR='#73DEC5'
OFF_COLOR='#E68A76'


class ConferenceApp:
    def __init__(self, master):
        self.master = master
        self.master.withdraw()
        self.master.title("Conference Client")
        self.client = ConferenceClient((SERVER_IP, MAIN_SERVER_PORT))

        self.master.geometry("800x600")

        self.username = simpledialog.askstring("Input", "Enter your name:", parent=self.master)

        if not self.username:
            self.username = "Guest"  # 如果用户没有输入姓名，默认使用 "Guest"

        self.client.username = self.username

        # self.master.withdraw()  # 隐藏主窗口
        self.hello_label = tk.Label(master, text=f"Hello {self.username}!", font=('Times New Roman', 14))
        self.hello_label.pack(anchor='n', padx=10, pady=10)

        # 创建会议按钮
        self.create_meeting_button = tk.Button(master, text="Create Meeting", width=20, height=2, bg='#00796B',
                                               fg='white', command=self.create_meeting)
        self.create_meeting_button.pack(expand=True)

        # 加入会议按钮
        self.join_meeting_button = tk.Button(master, text="Join Meeting", width=20, height=2, bg='#B2DFDB',
                                             fg='#212121', command=self.join_meeting)
        self.join_meeting_button.pack(expand=True)

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.camera_streaming = False
        self.capture_camera = None # cv2.VideoCapture(0)
        self.camera_window = None
        self.camera_container = None
        self.camera_canvas=None

        # self video
        self.video_streaming = False
        self.capture_video = None  # ImageGrab.grab()
        self.video_window = None
        self.video_container = None
        self.video_canvas = None

        #self.executor = ThreadPoolExecutor(max_workers=4)  # 创建线程池，线程数视需求调整

    def on_closing(self):
        if hasattr(self, 'meeting_window'):
            self.meeting_window.destroy()
       # await self.client.quit_conference()
        self.master.destroy()
        asyncio.get_event_loop().stop()  # 如果使用异步，可以调用此方法停止事件循环
        exit()

    # async def handle_audio(self):
    #     # 将接收和处理音频的任务放到线程池中
    #     await asyncio.to_thread(self.client.receive_audio)

    # async def handle_video(self):
    #     # 将接收和处理视频的任务放到线程池中
    #     await asyncio.to_thread(self.client.receive_video)

    def create_meeting(self):
        # 创建会议
        asyncio.create_task(self._async_create_meeting())

    async def _async_create_meeting(self):
        # 执行异步创建会议
        await self.client.create_conference()
        # 在任务完成后进行后续逻辑
        if self.client.on_meeting:
            self.open_meeting_window(self.client.conference_id)
            asyncio.create_task(self.run_receive_message())
            asyncio.create_task(self.client.receive_video())
            
            

    def join_meeting(self):
        conference_id = simpledialog.askstring("Input", "Enter Conference ID:", parent=self.master)
        if conference_id:
            asyncio.create_task(self._async_join_meeting(conference_id))

    async def _async_join_meeting(self, conference_id):

        await self.client.join_conference(conference_id)
        if self.client.on_meeting:
            self.open_meeting_window(conference_id)
            asyncio.create_task(self.run_receive_message())
            asyncio.create_task(self.client.receive_video())
            # # 创建协程任务
            # message_task = asyncio.create_task(self.run_receive_message())
            # audio_task = asyncio.create_task(self.handle_audio())
            # video_task = asyncio.create_task(self.handle_video())
            
            # # 并发运行
            # await asyncio.gather(message_task, audio_task, video_task)
            

#60198  60208
    def on_closing_meeting_window(self):
        self.on_closing()

    def open_meeting_window(self, conference_id):
        self.meeting_window = tk.Toplevel(self.master)
        self.meeting_window.title(f"Conference id: {conference_id}")
        self.meeting_window.geometry("700x1200")

        self.master.withdraw()

        self.meeting_window.protocol("WM_DELETE_WINDOW", self.on_closing_meeting_window)

        chat_frame = tk.Frame(self.meeting_window)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=15, padx=50)
        # 聊天窗区域
        chat_label = tk.Label(chat_frame, text=f'{self.username}\'s Chat', font=('Helvetica', 16))
        chat_label.pack(side=tk.TOP, pady=10)

        self.msg_scroll = tk.Scrollbar(chat_frame, orient="vertical")
        self.msg_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=15, padx=15)

        self.msg_display = scrolledtext.ScrolledText(chat_frame, width=40, height=30, state='disabled',
                                                     yscrollcommand=self.msg_scroll.set)
        self.msg_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.msg_entry = tk.Entry(chat_frame)
        self.msg_entry.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.send_button = tk.Button(chat_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.TOP, padx=10)

        control_frame = tk.Frame(chat_frame)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        self.microphone_button = tk.Button(control_frame, text="Unmute Microphone", command=self.unmute_microphone, bg=ON_COLOR,)
        self.microphone_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

        self.camera_button = tk.Button(control_frame, text="Turn On Camera", command=self.turn_on_camera, bg=ON_COLOR)
        self.camera_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

        self.video_button = tk.Button(control_frame, text="Turn On Screen Sharing", command=self.turn_on_video,bg=ON_COLOR)
        self.video_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

        self.leave_button = tk.Button(control_frame, text="Leave Meeting", command=self.leave_meeting,bg=OFF_COLOR)
        self.leave_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

        self.cancel_button = tk.Button(control_frame, text="Cancel Meeting", command=self.cancel_meeting)
        self.cancel_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

        self.switch_button = tk.Button(control_frame, text="Switch P2P", command=self.switch_mode)
        self.switch_button.pack(side=tk.TOP, padx=10, pady=5, fill=tk.X)

    def send_message(self):
        message = self.msg_entry.get()

        if not message.strip():
            return  # 防止发送空消息
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S") 
    
        self.msg_display.config(state='normal')
        # 在显示的消息前加上时间戳
        self.msg_display.insert(tk.END, f"[{timestamp}] You: {message}\n")
        self.msg_display.config(state='disabled')
        self.msg_entry.delete(0, tk.END)
        asyncio.create_task(self.client.send_message(message))

    async def run_receive_message(self):
        """运行接收消息的逻辑"""
        try:
            await self.client.receive_message(self.display_message)
        except Exception as e:
            self.display_message("Error", f"Failed to receive messages. {e}")

    def display_message(self, sender, message):
        """在聊天框中显示消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S") 
        self.msg_display.config(state='normal')
        
        self.msg_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        self.msg_display.config(state='disabled')

        if (message == 'quit'):
            self.meeting_window.destroy()
            self.master.deiconify()
            self.client.cs_conns = {}
            self.client.p2p_conns = {}
        if (message == 'p2p' and self.client.is_p2p == True):
            self.switch_button.config(text="Switch CS", command=self.switch_mode)
        elif (message == 'change CS' and self.client.is_p2p == False):
            self.switch_button.config(text="Switch P2P", command=self.switch_mode)
        elif (message == 'CS success' and self.client.is_p2p == False):
            self.switch_button.config(text="Switch P2P", command=self.switch_mode)

    async def _async_leaving_meeting(self):
        await self.client.quit_conference()
        if(self.client.on_meeting==False):
            self.meeting_window.destroy()
            self.master.deiconify()

    def leave_meeting(self):
        # TODO
        asyncio.create_task(self._async_leaving_meeting())

    def handle_microphone(self):
        if self.client.on_mic:
            self.unmute_microphone()
        else:
            self.mute_microphone()

    async def _async_cancel_meeting(self):
        await self.client.cancel_conference()
        if(self.client.on_meeting==False):
            self.meeting_window.destroy()
            self.master.deiconify()

    def cancel_meeting(self):
        asyncio.create_task(self._async_cancel_meeting())

    async def _async_switch_mode(self):
        await self.client.switch_p2p_server()
        if(self.client.is_p2p==True):
            self.switch_button.config(text="Switch CS", command=self.switch_mode)
            # asyncio.create_task(self.client.receive_video())
        else:
            self.switch_button.config(text="Switch P2P", command=self.switch_mode)
            # asyncio.create_task(self.run_receive_message())
            # asyncio.create_task(self.client.receive_video())

    def switch_mode(self):
        asyncio.create_task(self._async_switch_mode())

    def mute_microphone(self): # 关
        self.microphone_button.config(text="Unmute Microphone", command=self.unmute_microphone, bg=ON_COLOR)
        self.client.on_mic = False

    def unmute_microphone(self): # 开
        self.microphone_button.config(text="Mute Microphone", command=self.mute_microphone, bg=OFF_COLOR)
        self.client.on_mic = True
        asyncio.create_task(self.client.send_audio())

    # todo 屏幕共享与摄像头目前功能一样
    def turn_off_camera(self):
        if self.camera_streaming:
            self.camera_streaming = False
            self.capture_camera.release()
            self.camera_window.destroy()
            self.camera_button.config(text="Turn On Camera", bg=ON_COLOR, command=self.turn_on_camera)

    def turn_on_camera(self):
        # TODO
        # if not self.video_streaming:
        #     self.capture=capture_camera()
        # self.video_button.config(text="Turn Off Camera", command=self.turn_off_camera)
        # self.client.on_cam = True
        # asyncio.create_task(self.client.send_video())
        if not self.camera_streaming:
            self.capture_camera = cv2.VideoCapture(0)  # 0 表示默认摄像头
            if not self.capture_camera.isOpened():
                print("Error: Unable to access the camera.")
                return

            self.camera_window = tk.Toplevel(self.master)
            self.camera_window.title(f'{self.username}\'s Camera')
            self.camera_window.geometry("640x480")

            self.camera_canvas = tk.Canvas(self.camera_window, bg='white')
            self.camera_canvas.pack(fill=BOTH, expand=True)

            label = tk.Label(self.camera_window, text=f'{self.username}\'s Camera', width=15, height=1)
            label.pack()

            self.camera_streaming = True
            self.camera_button.config(text="Turn Off Camera", command=self.turn_off_camera, bg=OFF_COLOR)

            self.camera_window.after(10, self.update_frame_camera)
            # 开始读取和显示摄像头视频
            # asyncio.create_task(self.show_video_feed())

    def tk_camera(self):
        ref, frame = self.capture_camera.read()
        if not ref:
            print("Failed to capture frame")
            return None

        frame = cv2.flip(frame, 1)
        cvimage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)

        window_width = self.camera_window.winfo_width()
        window_height = self.camera_window.winfo_height()
        frame_height, frame_width = frame.shape[:2]

        aspect_ratio = frame_width / frame_height
        if window_width / window_height > aspect_ratio:
            new_height = window_height
            new_width = int(new_height * aspect_ratio)
        else:
            new_width = window_width
            new_height = int(new_width / aspect_ratio)

        pilImage = Image.fromarray(cvimage)
        pilImage = pilImage.resize((new_width, new_height), Image.LANCZOS)

        tkImage = ImageTk.PhotoImage(image=pilImage)
        return tkImage

    def update_frame_camera(self):
        pic = self.tk_camera()
        if pic:
            window_width = self.camera_window.winfo_width()
            window_height = self.camera_window.winfo_height()

            img_width = pic.width()
            img_height = pic.height()

            x_offset = (window_width - img_width) // 2
            y_offset = (window_height - img_height) // 2

            self.camera_canvas.create_image(x_offset, y_offset, anchor='nw', image=pic)
            self.camera_canvas.image = pic  # 保留图像引用，避免被垃圾回收
        else:
            print("No image to display")
        self.camera_window.after(10, self.update_frame_camera)  # 每10毫秒更新一次图像
    def turn_off_video(self):
        if self.video_streaming:
            self.video_streaming = False
            self.capture_video = None
            self.video_window.destroy()
            self.video_button.config(text="Turn On Screen Sharing", command=self.turn_on_video,bg=ON_COLOR)

    def turn_on_video(self):
        # TODO
        # self.video_button.config(text="Turn Off Screen Sharing", command=self.turn_off_video)
        # self.client.on_video = True
        # asyncio.create_task(self.client.send_video())
        if not self.video_streaming:
            self.video_window = tk.Toplevel(self.master)
            self.video_window.title(f'{self.username}\'s Screen Sharing')
            self.video_window.geometry("640x480")

            self.video_canvas = tk.Canvas(self.video_window, bg='white')
            self.video_canvas.pack(fill=tk.BOTH, expand=True)

            label = tk.Label(self.video_window, text=f'{self.username}\'s Screen', width=15, height=1)
            label.pack()

            self.video_streaming = True
            self.video_button.config(text="Turn Off Screen Sharing", command=self.turn_off_video,bg=OFF_COLOR)

            self.video_window.after(50, self.update_frame_video)

    def tk_capture(self):
        self.capture_video = ImageGrab.grab()
        screenshot = self.capture_video.convert("RGBA")

        # 获取当前窗口的尺寸
        window_width = self.video_window.winfo_width()
        window_height = self.video_window.winfo_height()
        pilImage = resize_image_to_fit_screen(screenshot, (window_width, window_height))
        tkImage = ImageTk.PhotoImage(image=pilImage)
        return tkImage

    def update_frame_video(self):
        pic = self.tk_capture()
        if pic:
            window_width = self.video_window.winfo_width()
            window_height = self.video_window.winfo_height()

            img_width = pic.width()
            img_height = pic.height()

            x_offset = (window_width - img_width) // 2
            y_offset = (window_height - img_height) // 2

            self.video_canvas.create_image(x_offset, y_offset, anchor='nw', image=pic)
            self.video_canvas.image = pic
        else:
            print("No image to display")

        self.video_window.after(50, self.update_frame_video)
    async def run(self):
        self.master.deiconify()  # 显示主窗口
        # self.master.mainloop()

        while True:
            self.master.update()
            await asyncio.sleep(0.01)  # 避免阻塞事件循环


if __name__ == "__main__":
    root = tk.Tk()
    app = ConferenceApp(root)
    # app.run()
    asyncio.run(app.run())
