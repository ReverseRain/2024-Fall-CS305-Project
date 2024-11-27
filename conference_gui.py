import tkinter as tk
from tkinter import simpledialog
import asyncio
from conf_client import ConferenceClient
from config import *

class ConferenceApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Conference Client")
        self.client = ConferenceClient(("SERVER_IP", MAIN_SERVER_PORT))

        self.master.geometry("800x600")

        # 创建会议按钮
        self.create_meeting_button = tk.Button(master, text="Create Meeting", width=20, height=2, bg='#00796B', fg='white',
                                               command=self.create_meeting)
        self.create_meeting_button.pack(expand=True)

        # 加入会议按钮
        self.join_meeting_button = tk.Button(master, text="Join Meeting", width=20, height=2, bg='#B2DFDB', fg='#212121',command=self.join_meeting)
        self.join_meeting_button.pack(expand=True)

    def create_meeting(self):
        asyncio.run(self.client.create_conference())

    def join_meeting(self):
        conference_id = simpledialog.askstring("Input", "Enter Conference ID:", parent=self.master)
        if conference_id:
            self.client.join_conference(conference_id)

    def run(self):
        self.master.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ConferenceApp(root)
    app.run()