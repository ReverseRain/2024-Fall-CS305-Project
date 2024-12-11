import asyncudp

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

    def setup_audio(self):
        """初始化音频流"""
        self.audio = pyaudio.PyAudio()
        self.streamin = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        self.streamout = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

    async def create_conference(self):
        try:
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
            writer.close()
            await writer.wait_closed()
            await self.start_conference()
        except Exception as e:
            self.show_info(f"[Error]: Unable to join conference. Error: {e}")

    async def quit_conference(self):
        """
        quit your on-going conference
        """
        try:
            # 初始化连接
            reader, writer = await asyncio.open_connection(self.server_addr[0], self.server_addr[1])
            self.show_info("[Info]: Connected to the server to quit the conference.")

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
                f"[Info]: Connected to message server: {self.conf_server_addr['message']} and video server: {self.conf_server_addr['video']}")

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
        stream=self.audio.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                input=True,
                                frames_per_buffer=CHUNK)
        reader, writer = self.conns['audio']
        print("[ConferenceClient]: Starting to send audio data...")

        try:
            while self.on_mic:
                # 从麦克风读取音频数据
                audio_data = capture_voice()

                # 发送音频数据到服务器
                writer.write(audio_data)
                await writer.drain()
        except Exception as e:
            print(f"[ConferenceClient]: Error while sending audio: {e}")
        finally:
            print("[ConferenceClient]: Closing audio stream")
            stream.stop_stream()
            stream.close()
            self.audio.terminate()
            writer.close()
            await writer.wait_closed()


    async def receive_audio(self):
        """接收来自其他客户端的音频数据并播放"""
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['audio']:
            self.show_info("[Error]: Not connected to the audio server.")
            return

        while self.on_meeting:
            if self.recv_data:
                # 播放音频数据
                self.play_audio(self.recv_data)
            await asyncio.sleep(0.01)

    def play_audio(self, audio_data):
        """播放接收到的音频数据"""
        self.streamout.write(audio_data)  # 播放音频

    async def start_audio(self):
        loop = asyncio.get_event_loop()

        # 创建音频发送的UDP端点
        self.audio_transport, self.audio_protocol = await loop.create_datagram_endpoint(
            lambda: AudioUDPProtocol(self),
            remote_addr=self.server_addr  # 服务器地址（IP, PORT）
        )

        # 启动音频发送和接收任务
        self.setup_audio()
        await asyncio.create_task(self.send_audio())
        await asyncio.create_task(self.receive_audio())

    async def send_video(self):
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['video']:
            self.show_info("[Error]: Not connected to the message server.")
            return

        try:

            reader, writer = self.conns['video']

            while self.on_video:
                screen_frame = capture_screen()
                # camera_frame = capture_camera()

                # 压缩帧
                compressed_screen = compress_image(screen_frame, format='JPEG', quality=85)
                # compressed_camera = compress_image(camera_frame, format='JPEG', quality=85)

                # print(compressed_screen.tell())

                # writer.write(compressed_camera)
                frame_length = len(compressed_screen).to_bytes(4, 'big')
                print(len(compressed_screen))
                writer.write(frame_length + compressed_screen)
                await writer.drain()
                self.show_info(f"[Info]: sending video")
                await asyncio.sleep(5)

            writer.write(b'\x00\x00\x00\x00')
            await writer.drain()
            print("[Info]: Sent stop video signal.")



        except Exception as e:
            self.show_info(f"[Error]: Failed to send message. Error: {e}")
            writer.write(b'\x00\x00\x00\x00')
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
            sock = self.conns['video']
            self.show_info("[Info]: Listening for incoming video frames.")

            while True:
                data = await sock.recvfrom()  # 假设消息头大小为 1024 字节
                if not data:
                    break  # 如果没有接收到数据，退出接收

                # _, payload = data[:4], data = data[4:]
                # length = struct.unpack('>I', payload)[0]

                # # 接收完整的视频帧
                # while len(payload) < length:
                #     payload += await reader.read(length - len(payload))

                frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is None:
                    print("Failed to decode frame.")
                    continue

                # 显示帧（这里仅作为示例，实际应用中可能需要保存或进一步处理）
                cv2.imshow('Received Frame', frame)
                cv2.waitKey(1)

        except Exception as e:
            self.show_info(f"[Error]: Failed to receive video frame. Error: {e}")

        finally:
            self.show_info("[Info]: Stopped receiving video frames.")

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
