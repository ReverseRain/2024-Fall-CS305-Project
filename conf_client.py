<<<<<<< HEAD

=======
import wave

import asyncudp
>>>>>>> 28f661c6fdcccc369bdb93ec864e231951debeea

from util import *
import asyncio
import json
from config import *
import struct


class ConferenceClient:
    def __init__(self, server_addr):
        # sync client
        self.is_working = True
        self.server_addr = server_addr  # server addr
        self.on_meeting = False  # status
        self.conf_server_addr = {}
        self.conns = {}  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_id = None

        self.conference_info = None  # you may need to save and update some conference_info regularly

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

        self.username = None
        self.on_video = False

        self.on_mic = False
<<<<<<< HEAD
   
=======

    def setup_audio(self):
        """初始化音频流"""
        self.audio = pyaudio.PyAudio()
        self.streamin = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        self.streamout = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

>>>>>>> 28f661c6fdcccc369bdb93ec864e231951debeea
    async def create_conference(self):
        try:
            if self.on_meeting:
                self.show_info("[Info]: You are on meeting CANNOT create a conference.")
                return
            # 初始化连接
            reader, writer = await asyncio.open_connection(self.server_addr[0], self.server_addr[1])
            self.show_info("[Info]: Connected to the server for creating a conference.")

            # 构造创建会议的请求数据
            request_data = "create_conference"

            writer.write(request_data.encode('utf-8'))
            await writer.drain()

            # 接收服务器响应
            response = await reader.read(1024)
            response_data = json.loads(response.decode('utf-8'))

            if response_data.get("status") == "success":
                self.conference_info = response_data["conference_info"]
                self.on_meeting = True
                self.conference_id = self.conference_info['conference_id']
                self.conf_server_addr['message'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_message_port'])
                self.conf_server_addr['video'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_video_port'])
                self.conf_server_addr['audio'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_audio_port'])
                # print(self.conf_server_addr['message'])
                self.show_info(f"[Success]: Conference created with ID: {self.conference_id}")
            else:
                self.show_info(f"[Error]: Failed to create conference. Reason: {response_data.get('message')}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()

            await self.start_conference()
        except Exception as e:
            self.show_info(f"[Error]: Unable to create conference. Error: {e}")

    async def join_conference(self, conference_id):
        """
        Join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        try:
            if self.on_meeting:
                self.show_info("[Info]: You are on meeting CANNOT join a conference.")
                return
            # 初始化连接
            reader, writer = await asyncio.open_connection(self.server_addr[0], self.server_addr[1])
            self.show_info(f"[Info]: Connected to the server to join conference with ID: {conference_id}.")

            # 构造加入会议的请求数据
            request_data = f"join_conference {conference_id}"
            writer.write(request_data.encode('utf-8'))
            await writer.drain()

            # 接收服务器响应
            response = await reader.read(1024)
            response_data = json.loads(response.decode('utf-8'))

            if response_data.get("status") == "success":
                # 会议加入成功
                self.conference_info = response_data["conference_info"]
                self.on_meeting = True
                self.conference_id = conference_id
                self.conf_server_addr['message'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_message_port'])
                self.conf_server_addr['video'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_video_port'])
                self.conf_server_addr['audio'] = (
                    self.conference_info['conference_ip'], self.conference_info['conference_audio_port'])
                self.show_info(f"[Success]: Successfully joined conference with ID: {self.conference_id}")
            else:
                # 会议加入失败
                self.show_info(f"[Error]: Failed to join conference. Reason: {response_data.get('message')}")

            # 关闭连接
            await self.start_conference()
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            self.show_info(f"[Error]: Unable to join conference. Error: {e}")

    async def quit_conference(self):
        """
        quit your on-going conference
        """
        try:
            if not self.on_meeting:
                self.show_info("[Info]: You are not on meeting ." )
                return
            # 初始化连接
            reader, writer = self.conns['message']

            # 构造消息数据
            message_data = {
                "sender": self.username,
                "message": message
            }

            request_data = "quit_conference " + str(self.conference_id)

            writer.write(request_data.encode('utf-8'))
            await writer.drain()

            # 接收服务器响应
            response = await reader.read(1024)
            response_data = json.loads(response.decode('utf-8'))

            if response_data.get("status") == "success":
                self.on_meeting = False
                self.on_mic = False
                self.show_info("[Success]: Successfully quit the conference.")
            else:
                self.show_info(f"[Error]: Failed to quit conference. Reason: {response_data.get('message')}")
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.show_info(f"[Error]: Unable to quit conference. Error: {e}")

    async def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        try:
            if not self.on_meeting:
                self.show_info("[Info]: You are not on meeting ." )
                return
            # 初始化连接
            reader, writer = await asyncio.open_connection(self.server_addr[0], self.server_addr[1])
            self.show_info("[Info]: Connected to the server to cancel the conference.")

            request_data = "cancel_conference " + str(self.conference_id)

            writer.write(request_data.encode('utf-8'))
            await writer.drain()

            # 接收服务器响应
            response = await reader.read(1024)
            response_data = json.loads(response.decode('utf-8'))

            if response_data.get("status") == "success":
                self.on_meeting = False
                self.show_info("[Success]: Successfully cancelled the conference.")
            else:
                self.show_info(f"[Error]: Failed to cancel conference. Reason: {response_data.get('message')}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.show_info(f"[Error]: Unable to cancel conference. Error: {e}")

    async def send_message(self, message):
        """
        发送消息到服务器，广播给所有在会议中的客户端
        """
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['message']:
            self.show_info("[Error]: Not connected to the message server.")
            return

        try:
            reader, writer = self.conns['message']

            # 构造消息数据
            message_data = {
                "sender": self.username,
                "message": message
            }
            print("message_data: ", message_data)
            request_data = json.dumps(message_data)
            writer.write(request_data.encode('utf-8'))
            await writer.drain()
            self.show_info(f"[Info]: Message sent: {message}")

            # 接收服务器回应（确认收到消息）
            # response = await reader.read(1024)
            # self.show_info(f"[Info]: Server response: {response.decode('utf-8')}")

            # 关闭连接
            # writer.close()
            # await writer.wait_closed()

        except Exception as e:
            self.show_info(f"[Error]: Failed to send message. Error: {e}")

    async def receive_message(self, message_callback):
        """
        接收来自会议中的其他客户端的消息
        """
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['message']:
            self.show_info("[Error]: Not connected to the message server.")
            return

        try:
            reader, writer = self.conns['message']
            self.show_info("[Info]: Listening for incoming messages.")

            while True:
                # 接收消息数据
                response = await reader.read(1024)
                if not response:
                    break  # 如果没有接收到数据，退出接收
                # print(response)
                message_data = json.loads(response.decode('utf-8'))
                sender = message_data.get("sender")
                message = message_data.get("message")
                self.show_info(f"[New Message]-{sender}:{message}")
                message_callback(sender, message)

            # 关闭连接
            # writer.close()
            # await writer.wait_closed()

        except Exception as e:
            self.show_info(f"[Error]: Failed to receive messages. Error: {e}")

    def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        pass

    def share_switch(self, data_type):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        pass

    def keep_recv(self, recv_conn, data_type, decompress=None):
        '''
        running task: keep receiving certain type of data (save or output)
        you can create other functions for receiving various kinds of data
        '''

    def output_data(self):
        '''
        running task: output received stream data
        '''

    async def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''
        if not self.on_meeting:
            print("[Error]: You are not in a meeting yet.")
            return

        try:
            if 'message' not in self.conns:
                self.conns['message'] = await asyncio.open_connection(self.conf_server_addr['message'][0],
                                                                      self.conf_server_addr['message'][1])
            if 'video' not in self.conns:
                self.conns['video'] = await asyncio.open_connection(self.conf_server_addr['video'][0],
                                                                    self.conf_server_addr['video'][1])
            if 'audio' not in self.conns:
                self.conns['audio'] = await asyncio.open_connection(self.conf_server_addr['audio'][0],
                                                                    self.conf_server_addr['audio'][1])
            #         connect = asyncio.get_event_loop().create_datagram_endpoint(
            #     lambda: EchoUDPClientProtocol(),
            #     remote_addr=(self.conf_server_addr['video'][0], self.conf_server_addr['video'][1])
            # )
            #         transport, protocol = await connect
            #         self.conns['video']=(transport,protocol)

            print(
                f"[Info]: Connected to message server: {self.conf_server_addr['message']}  video server: {self.conf_server_addr['video']} audio server: {self.conf_server_addr['audio']}")

            print("[Info]: Conference started successfully.")
        except Exception as e:
            print(f"[Error]: Failed to start the conference. Error: {e}")

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''
        try:
            for conn in self.conns.values():
                if isinstance(conn, asyncio.StreamWriter):
                    conn.close()
                # if isinstance(conn, asyncudp.UDPSocket):
                #     conn.close()

            self.conns.clear()

            print("[Info]: All connections closed.")

            self.on_meeting = False
            print("[Info]: Conference closed successfully.")
        except Exception as e:
            print(f"[Error]: Failed to close the conference. Error: {e}")

    def show_info(self, info):
        print(info)

    async def async_input(self, prompt):
        """异步获取用户输入"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, prompt)

    async def handle_input(self):
        """从用户输入中获取消息并发送"""
        while True:
            user_input = await self.async_input("[You]: ")
            if user_input.strip():  # 如果用户输入了内容
                await self.send_message(user_input)

    async def send_audio(self):
        """从麦克风捕获音频并通过UDP发送到服务器"""
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['audio']:
            self.show_info("[Error]: Not connected to the server.")
            return
<<<<<<< HEAD
        self.on_mic=True
        
=======
        # stream=self.audio.open(format=pyaudio.paInt16,
        #                         channels=0,
        #                         rate=16000,
        #                         input=True,
        #                         frames_per_buffer=CHUNK)
        reader, writer = self.conns['audio']
>>>>>>> 28f661c6fdcccc369bdb93ec864e231951debeea
        print("[ConferenceClient]: Starting to send audio data...")

        ##################### 打开WAV文件，用于保存音频数据
        output_filename = 'output_audio.wav'
        wf = wave.open(output_filename, 'wb')
        ##############################################

        try:
<<<<<<< HEAD

            reader, writer = self.conns['audio']
=======
            ################################## 设置WAV文件的参数
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))  # 16-bit音频
            wf.setframerate(16000)  # 采样率16kHz
            ##############################################
>>>>>>> 28f661c6fdcccc369bdb93ec864e231951debeea
            while self.on_mic:
                # 从麦克风读取音频数据
                audio_data = self.capture_voice()
                # print(audio_data)

                ##################### 将音频数据写入WAV文件
                wf.writeframes(audio_data)
                ##############################################

                # 发送音频数据到服务器
                writer.write(audio_data)
                await writer.drain()
                self.show_info(f"[Info]: sending audio len {len(audio_data)}")
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"[ConferenceClient]: Error while sending audio: {e}")
        finally:
            print("[ConferenceClient]: Closing audio stream")
<<<<<<< HEAD
            streamin.stop_stream()
            streamin.close()
=======
            self.streamin.stop_stream()
            self.streamin.close()
            self.audio.terminate()
>>>>>>> 28f661c6fdcccc369bdb93ec864e231951debeea
            writer.close()
            await writer.wait_closed()

    def capture_voice(self):
        return self.streamin.read(CHUNK)
    async def receive_audio(self):
        """接收来自其他客户端的音频数据并播放"""
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['audio']:
            self.show_info("[Error]: Not connected to the audio server.")
            return
        try:
            reader, writer = self.conns['audio']
            self.show_info("[Info]: Listening for incoming audio frames.")

            while True:
                audio_data=reader.readexactly(2048)
                    # 播放音频数据
                streamout.write(audio_data)
                await asyncio.sleep(0.01)
        except Exception as e:
            self.show_info(f"[Error]: Failed to receive audio frame. Error: {e}")

    def play_audio(self, audio_data):
        """播放接收到的音频数据"""
        self.streamout.write(audio_data)  # 播放音频

    async def send_video(self):
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['video']:
            self.show_info("[Error]: Not connected to the message server.")
            return
        
        self.on_video=True

        try:

            reader, writer = self.conns['video']
            sender_addr = writer.get_extra_info('sockname')
            sender_addr_str = f"{sender_addr[0]}:{sender_addr[1]}"  # 将地址格式化为字符串，如 "127.0.0.1:12345"
            sender_addr_bytes = sender_addr_str.encode('utf-8')  # 转换为字节串
            address_length = len(sender_addr_bytes)
            
            print(f'sender addr {sender_addr_str}')

            while self.on_video:
                screen_frame = capture_screen()
                #camera_frame = capture_camera()
                

                # 压缩帧
                compressed_screen = compress_image(screen_frame, format='JPEG', quality=85)
                # frame = cv2.imdecode(np.frombuffer(compressed_screen, dtype=np.uint8), cv2.IMREAD_COLOR)

                # print(compressed_screen.tell())

                # writer.write(compressed_camera)
                frame_length = len(compressed_screen).to_bytes(4, 'big')
                print(len(compressed_screen))
                total_length =  4 + 4 + address_length + len(compressed_screen)
                #4byte 地址长度 + 4byte 数据帧长度 + 地址 +数据

                frame_length_bytes = len(compressed_screen).to_bytes(4, 'big')
                address_length_bytes=address_length.to_bytes(4,'big')
                total_length_bytes = total_length.to_bytes(4, 'big')
                packet = total_length_bytes + address_length_bytes +frame_length_bytes+ sender_addr_bytes + compressed_screen
                writer.write(packet)
                await writer.drain()
                self.show_info(f"[Info]: sending video")
                await asyncio.sleep(0.03)
            
            #cv2.destroyWindow('self')
            total_length =  4 + 4 + address_length
            #4byte 地址长度 + 4byte 数据帧长度 + 地址
            address_length_bytes=address_length.to_bytes(4,'big')
            total_length_bytes = total_length.to_bytes(4, 'big')
            frame_length_bytes=(0).to_bytes(4,'big')
            stop_packet = total_length_bytes + address_length_bytes +frame_length_bytes+ sender_addr_bytes 
            
            writer.write(stop_packet)
            await writer.drain()
            print("[Info]: Sent stop video signal.")



        except Exception as e:
            self.show_info(f"[Error]: Failed to send video. Error: {e}")
            #cv2.destroyWindow('self')
            total_length =  4 + 4 + address_length
            #4byte 地址长度 + 4byte 数据帧长度 + 地址
            address_length_bytes=address_length.to_bytes(4,'big')
            total_length_bytes = total_length.to_bytes(4, 'big')
            frame_length_bytes=(0).to_bytes(4,'big')
            stop_packet = total_length_bytes + address_length_bytes +frame_length_bytes+ sender_addr_bytes 
            
            writer.write(stop_packet)
            await writer.drain()
            print("[Info]: Sent stop video signal.")
        
    async def receive_video(self):
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['video']:
            self.show_info("[Error]: Not connected to the video server.")
            return

        try:
            reader, writer = self.conns['video']
            self.show_info("[Info]: Listening for incoming video frames.")

            self_addr = writer.get_extra_info('sockname')
            self_addr_str = f"{self_addr[0]}:{self_addr[1]}" 
           

            # 存储每个发送者地址的帧索引
            sender_frames = {}
            max_width, max_height = 1800, 1000  # 大窗口的尺寸
            frame_width, frame_height = 900, 500  # 每个视频帧的显示区域大小
            cols = max_width // frame_width  # 每行显示的帧数
            # 创建一个大窗口，初始化黑色背景
            canvas = np.zeros((max_height, max_width, 3), dtype=np.uint8)

            while True:
                # 读取总长度（4字节）
                total_length_data = await reader.readexactly(4)
                total_length = int.from_bytes(total_length_data, 'big')

                # 读取地址长度（4字节）
                address_length_data = await reader.readexactly(4)
                address_length = int.from_bytes(address_length_data, 'big')

                # 读取视频帧长度（4字节）
                frame_length_data = await reader.readexactly(4)
                frame_length = int.from_bytes(frame_length_data, 'big')

                # 读取发送者地址
                sender_addr_data = await reader.readexactly(address_length)
                sender_addr_str = sender_addr_data.decode('utf-8')


                if frame_length == 0:
                    print(f"[{sender_addr_str}]: Received stop signal. Removing from display.")
                    if sender_addr_str in sender_frames:
                       
                        del sender_frames[sender_addr_str]
                        canvas.fill(0)
                        for i, (addr, frame) in enumerate(sender_frames.items()):
                            row, col = divmod(i, cols)
                            if row * frame_height >= max_height:  # 超过窗口大小则跳过
                                break
                            x, y = col * frame_width, row * frame_height
                            canvas[y:y + frame_height, x:x + frame_width] = cv2.resize(frame, (frame_width, frame_height))
                            # 显示发送者地址
                            if addr==self_addr_str:
                                cv2.putText(canvas, 'YOU', (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                            else:
                                cv2.putText(canvas, addr, (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                        # 显示大窗口
                        cv2.imshow("Video Conference", canvas)
                        cv2.waitKey(1)
                    continue

                # 读取视频帧数据
                frame_data = await reader.readexactly(frame_length)
                if len(frame_data)==0:
                    continue
                frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is None:
                    print("Failed to decode frame.")
                    continue

                # 如果是新发送者，添加到 sender_frames
                #if sender_addr_str not in sender_frames:
                sender_frames[sender_addr_str] = frame

               

                

                # 绘制所有发送者的帧到大窗口
                for i, (addr, frame) in enumerate(sender_frames.items()):
                    row, col = divmod(i, cols)
                    if row * frame_height >= max_height:  # 超过窗口大小则跳过
                        break
                    x, y = col * frame_width, row * frame_height
                    canvas[y:y + frame_height, x:x + frame_width] = cv2.resize(frame, (frame_width, frame_height))
                    # 显示发送者地址
                    if addr==self_addr_str:
                        cv2.putText(canvas, 'YOU', (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    else:
                        cv2.putText(canvas, addr, (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                # 显示大窗口
                cv2.imshow("Video Conference", canvas)
                cv2.waitKey(1)

        except Exception as e:
            self.show_info(f"[Error]: Failed to receive video frame. Error: {e}")

        finally:
            self.show_info("[Info]: Stopped receiving video frames.")
            cv2.destroyAllWindows()

            

    # async def receive_video(self):
    #     if not self.on_meeting:
    #         self.show_info("[Error]: You are not in a conference.")
    #         return

    #     if not self.conns['video']:
    #         self.show_info("[Error]: Not connected to the video server.")
    #         return

    #     try:
    #         reader, writer = self.conns['video']
    #         self.show_info("[Info]: Listening for incoming video frames.")

    #         # 存储每个发送者地址对应的窗口名称
    #         sender_windows = {}

    #         while True:
    #             # 读取总长度（4字节）
    #             total_length_data = await reader.readexactly(4)
    #             total_length = int.from_bytes(total_length_data, 'big')

                

    #             # 读取地址长度（4字节）
    #             address_length_data = await reader.readexactly(4)
    #             address_length = int.from_bytes(address_length_data, 'big')

    #             # 读取视频帧长度（4字节）
    #             frame_length_data = await reader.readexactly(4)
    #             frame_length = int.from_bytes(frame_length_data, 'big')

    #             # 读取发送者地址
    #             sender_addr_data = await reader.readexactly(address_length)
    #             sender_addr_str = sender_addr_data.decode('utf-8')

    #             if total_length==0:
    #                 print(f"[{sender_addr_str}]: Received stop signal. Closing display.")
    #                 cv2.destroyWindow(sender_windows[sender_addr_str])
    #                 continue


    #             # 读取视频帧数据
    #             frame_data = await reader.readexactly(frame_length) 
    #             frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

    #             if frame is None:
    #                 print("Failed to decode frame.")
    #                 continue

    #             # 如果该发送者地址的窗口还没打开，创建一个新的窗口
    #             if sender_addr_str not in sender_windows:
    #                 sender_windows[sender_addr_str] = f"Received Frame from {sender_addr_str}"

    #             # 显示该发送者的视频帧
    #             cv2.imshow(sender_windows[sender_addr_str], frame)
    #             cv2.waitKey(1)

    #     except Exception as e:
    #         self.show_info(f"[Error]: Failed to receive video frame. Error: {e}")

    #     finally:
    #         self.show_info("[Info]: Stopped receiving video frames.")
    #         cv2.destroyAllWindows()


    async def video_test(self):
        """启动会议客户端，并同时处理发送和接收消息"""

        try:
            # 初始化连接
            # if(self.conns['message']!=None):
            self.conns['message'] = await asyncio.open_connection(self.conf_server_addr['message'][0],
                                                                  self.conf_server_addr['message'][1])
            self.conns['video'] = await asyncudp.create_socket(
                remote_addr=(self.conf_server_addr['video'][0], self.conf_server_addr['video'][1]))
            print(self.conf_server_addr['video'][1])
            self.show_info(f"[Info]: Connected to the conference {self.conference_id} message server")

            # 启动接收消息的任务
            # receive_task = asyncio.create_task(self.receive_video())

            # 启动处理输入并发送消息的任务
            # input_task = asyncio.create_task(self.send_video())

            # 等待任务完成
            # await asyncio.gather(receive_task, input_task)

        except Exception as e:
            self.show_info(f"[Error]: Failed to start the conference client. Error: {e}")

    async def message_test(self):
        """启动会议客户端，并同时处理发送和接收消息"""

        try:
            # 初始化连接
            self.conns['message'] = await asyncio.open_connection(self.conf_server_addr['message'][0],
                                                                  self.conf_server_addr['message'][1])
            self.show_info(f"[Info]: Connected to the conference {self.conference_id} message server")

            # 启动接收消息的任务
            receive_task = asyncio.create_task(self.receive_message())

            # 启动处理输入并发送消息的任务
            input_task = asyncio.create_task(self.handle_input())

            # 等待任务完成
            await asyncio.gather(receive_task, input_task)

        except Exception as e:
            self.show_info(f"[Error]: Failed to start the conference client. Error: {e}")

    def start(self):
        """
        execute functions based on the command line input
        """
        while True:
            if self.on_meeting:
                status = f'OnMeeting-{self.conference_id}'
                # asyncio.run(self.video_test())
            else:
                status = 'Free'

                recognized = True
                cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
                fields = cmd_input.split(maxsplit=1)
                if len(fields) == 1:
                    if cmd_input in ('?', '？'):
                        print(HELP)
                    elif cmd_input == 'create':
                        asyncio.run(self.create_conference())
                    elif cmd_input == 'cancel':
                        asyncio.run(self.cancel_conference())
                    else:
                        recognized = False
                elif len(fields) == 2:
                    if fields[0] == 'join':
                        input_conf_id = fields[1]
                        if input_conf_id.isdigit():
                            asyncio.run(self.join_conference(input_conf_id))
                        else:
                            print('[Warn]: Input conference ID must be in digital form')
                    elif fields[0] == 'switch':
                        data_type = fields[1]
                        if data_type in self.share_data.keys():
                            self.share_switch(data_type)
                    elif fields[0] == 'quit':
                        asyncio.run(self.quit_conference())
                    else:
                        recognized = False
                else:
                    recognized = False

                if not recognized:
                    print(f'[Warn]: Unrecognized cmd_input {cmd_input}')


class EchoUDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print(f"Received response: {message} from {addr}")
        # 调用回调函数处理响应

    def error_received(self, exc):
        print(f"Error received: {exc}")
        self.transport.close()


class AudioUDPProtocol:
    def __init__(self, client):
        self.client = client

    def datagram_received(self, data, addr):
        """接收到音频数据后播放"""
        self.client.recv_data = data  # 保存接收到的音频数据


if __name__ == '__main__':
    client1 = ConferenceClient((SERVER_IP, MAIN_SERVER_PORT))
    client1.start()
