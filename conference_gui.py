import tkinter as tk
from tkinter import simpledialog, scrolledtext
import asyncio
from conf_client import ConferenceClient
from config import *


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

        self.client.username=self.username

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
        

    def on_closing(self):
        if hasattr(self, 'meeting_window'):
            self.meeting_window.destroy()
        self.client.quit_conference()
        self.master.destroy()

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

    def join_meeting(self):
        conference_id = simpledialog.askstring("Input", "Enter Conference ID:", parent=self.master)
        if conference_id:
            asyncio.create_task(self._async_join_meeting(conference_id))
            
    async def _async_join_meeting(self,conference_id):

        await self.client.join_conference(conference_id)
        if self.client.on_meeting:
            self.open_meeting_window(conference_id)
            asyncio.create_task(self.run_receive_message())

    def on_closing_meeting_window(self):
        self.on_closing()

    def open_meeting_window(self, conference_id):
        self.meeting_window = tk.Toplevel(self.master)
        self.meeting_window.title(f"Conference id: {conference_id}")
        self.meeting_window.geometry("1800x900")

        frame_left = tk.Frame(self.meeting_window)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        frame_right = tk.Frame(self.meeting_window)
        frame_right.pack(side=tk.RIGHT)

        self.master.withdraw()

        self.meeting_window.protocol("WM_DELETE_WINDOW", self.on_closing_meeting_window)

        win_height = 900
        win_width = 1800
        frame_right_width = int(win_width / 4)
        frame_right.config(width=frame_right_width)
        frame_left.config(width=win_width - frame_right_width)

        # 视频显示区域
        self.video_area = tk.Label(frame_left)
        self.video_area.pack()

        # 聊天窗区域
        chat_label = tk.Label(frame_right, text="Chat", font=('Helvetica', 16))
        chat_label.pack(side=tk.TOP, pady=10)
        self.msg_scroll = tk.Scrollbar(frame_right, orient="vertical")
        self.msg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_display = scrolledtext.ScrolledText(frame_right, width=40, height=30, state='disabled',
                                                     yscrollcommand=self.msg_scroll.set)
        self.msg_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.msg_entry = tk.Entry(frame_right)
        self.msg_entry.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.send_button = tk.Button(frame_right, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.TOP, padx=10)

        control_frame = tk.Frame(frame_left, height=100)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # 按钮框架
        button_frame = tk.Frame(control_frame)
        button_frame.pack(side=tk.TOP, pady=10)

        self.microphone_button = tk.Button(button_frame, text="Mute Microphone", command=self.mute_microphone)
        self.microphone_button.pack(side=tk.LEFT, padx=10)

        self.video_button = tk.Button(button_frame, text="Turn On Video", command=self.turn_on_video)
        self.video_button.pack(side=tk.LEFT, padx=10)

        self.leave_button = tk.Button(button_frame, text="Leave Meeting", command=self.leave_meeting)
        self.leave_button.pack(side=tk.LEFT, padx=10)

    def send_message(self):
        message = self.msg_entry.get()
    
        if not message.strip():
            return  # 防止发送空消息
        
        self.msg_display.config(state='normal')
        self.msg_display.insert(tk.END, "You: " + message + "\n")
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
        self.msg_display.config(state='normal')
        self.msg_display.insert(tk.END, f"{sender}: {message}\n")
        self.msg_display.config(state='disabled')

    def leave_meeting(self):
        # TODO
        asyncio.run(self.client.quit_conference())
        self.meeting_window.destroy()
        self.master.deiconify()

    def mute_microphone(self):
        self.microphone_button.config(text="Unmute Microphone", command=self.unmute_microphone)
        # TODO
        pass

    def unmute_microphone(self):
        self.microphone_button.config(text="Mute Microphone", command=self.mute_microphone)
        pass

    def turn_off_video(self):
        # TODO
        self.video_button.config(text="Turn On Video", command=self.turn_on_video)
        self.client.on_video=False
       

    def turn_on_video(self):
        # TODO
        self.video_button.config(text="Turn Off Video", command=self.turn_off_video)
        self.client.on_video=True
        asyncio.create_task(self.client.send_video())
        
   

    async def run(self):
        self.master.deiconify()  # 显示主窗口
        #self.master.mainloop()
        
        while True:
            self.master.update()
            await asyncio.sleep(0.01)  # 避免阻塞事件循环


if __name__ == "__main__":
    root = tk.Tk()
    app = ConferenceApp(root)
    #app.run()
    asyncio.run(app.run())
