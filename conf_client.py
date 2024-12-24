from util import *
import asyncio
import json
from config import *
import struct
import threading



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
        self.p2p_addr = {}

        self.username=None
        self.on_video=False
        self.is_owner=False
        self.is_p2p=False

        self.p2p_message_server=None
        self.p2p_video_server=None
        self.cs_conns = {}
        self.p2p_conns = {}

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
                self.is_owner = True
                self.conference_id = self.conference_info['conference_id']
                self.conf_server_addr['message'] = (
                self.conference_info['conference_ip'], self.conference_info['conference_message_port'])
                self.conf_server_addr['video'] = (
                self.conference_info['conference_ip'], self.conference_info['conference_video_port'])
                # print(self.conf_server_addr['message'])
                self.show_info(f"[Success]: Conference created with ID: {self.conference_id}")
            else:
                self.show_info(f"[Error]: Failed to create conference. Reason: {response_data.get('message')}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()
            # self.on_video=True

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
            if(self.is_owner):
                print("owner can only cancel the conf")
                return
            await self.send_message('quit')
            self.cs_conns={}
            self.p2p_conns={}

            # 接收服务器响应
            
            self.on_meeting = False
            self.show_info("[Success]: Successfully quit the conference.")
            

        except Exception as e:
            self.show_info(f"[Error]: Unable to quit conference. Error: {e}")

    async def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        try:
            # 初始化连接
            if(self.is_owner!=True):
                return
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
            self.cs_conns={}
            self.p2p_conns={}

            self.is_owner=False
            return
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

    async def receive_message(self,message_callback):
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
                reader, writer = self.conns['message']
                # print('now recieve port',writer.get_extra_info('socket').getsockname()[1])
                # 接收消息数据
                response = await reader.read(1024)
                if not response:
                    break  # 如果没有接收到数据，退出接收
                message_data = json.loads(response.decode('utf-8'))
                sender = message_data.get("sender")
                message = message_data.get("message")
                self.show_info(f"[New Message]-{sender}:{message}")
                if(message=="conf close"):
                    self.on_meeting=False
                    await self.quit_conference()
                elif("message_ports" in message_data):
                    await self.switch_p2p_client(message_data.get("ip"),message_data.get("message_ports"),message_data.get("video_ports"))
                elif(message=="change CS"):
                    await self.switch_p2p_client()
                elif(message=="No"):
                    self.is_p2p=False
                message_callback(sender, message)

            # 关闭连接
            # writer.close()
            # await writer.wait_closed()
            print("退出")

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
            if 'message' not in self.cs_conns:
                self.cs_conns['message']=await asyncio.open_connection(self.conf_server_addr['message'][0], self.conf_server_addr['message'][1])
                
            self.conns['message'] = self.cs_conns['message']
            if 'video' not in self.cs_conns:
                self.cs_conns['video']= await asyncio.open_connection(self.conf_server_addr['video'][0], self.conf_server_addr['video'][1])
            self.conns['video']=self.cs_conns['video']
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

    async def send_video(self,reader=None,writer=None):
        if not self.on_meeting:
            self.show_info("[Error]: You are not in a conference.")
            return

        if not self.conns['video']:
            self.show_info("[Error]: Not connected to the message server.")
            return
        
        

        try:
            if(reader==None and writer==None):
                reader, writer = self.conns['video']
            sender_addr = writer.get_extra_info('sockname')
            sender_addr_str = f"{sender_addr[0]}:{sender_addr[1]}"  # 将地址格式化为字符串，如 "127.0.0.1:12345"
            sender_addr_bytes = sender_addr_str.encode('utf-8')  # 转换为字节串
            address_length = len(sender_addr_bytes)
            
            print(f'sender addr {sender_addr_str}')

            while self.on_video:
                # screen_frame = capture_screen()
                camera_frame = capture_camera()

                # 压缩帧
                # compressed_screen = compress_image(screen_frame, format='JPEG', quality=85)
                compressed_screen = compress_image(camera_frame, format='JPEG', quality=85)

                # cv2.imshow('self', frame)
                # cv2.waitKey(1)  # 等待1毫秒来处理OpenCV事件
               
                
                
                total_length =  4 + 4 + address_length + len(compressed_screen)
                #4byte 地址长度 + 4byte 数据帧长度 + 地址 +数据

                frame_length_bytes = len(compressed_screen).to_bytes(4, 'big')
                address_length_bytes=address_length.to_bytes(4,'big')
                total_length_bytes = total_length.to_bytes(4, 'big')
                packet = total_length_bytes + address_length_bytes +frame_length_bytes+ sender_addr_bytes + compressed_screen
                writer.write(packet)
                await writer.drain()
                self.show_info(f"[Info]: sending video")

                await asyncio.sleep(0.01)
            
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
                reader, writer = self.conns['video']
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
                else:
                    print("reveive new video")
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
                
                #如果是p2p则发生回声音
                if(self.is_p2p==True and self.p2p_video_server==None):
                    packet=total_length_data + address_length_data +frame_length_data+ sender_addr_data + frame_data
                    writer.write(packet)
                    await writer.drain()
                

        except Exception as e:
            self.show_info(f"[Error]: Failed to receive video frame. Error: {e}")

        finally:
            self.show_info("[Info]: Stopped receiving video frames.")
            cv2.destroyAllWindows()

    async def check_p2p(self):
        await self.send_message('p2p')
        reader,writer=self.conns['message']

    async def p2p_message(self,reader,writer):  
        reader1,writer1=self.cs_conns['message']
        if('message' not in self.p2p_conns):
            self.p2p_conns['message']=(reader,writer)
            self.conns['message']=self.p2p_conns['message']
            change_data={
                "sender":self.username,
                "message":"new mode message start"
            }
            writer1.write(json.dumps(change_data).encode('utf-8'))
            await writer1.drain()
        else:
            response = await reader.read(1024)
            message_data = json.loads(response.decode('utf-8'))
            message = message_data.get("message")
            if(message=="p2p only for 2 clients change to cs"):
                await self.switch_p2p_server()

    async def p2p_video(self,reader,writer):  

        reader1,writer1=self.cs_conns['video']
        self.p2p_conns['video']=(reader,writer)
        self.conns['video']=self.p2p_conns['video']
        await self.send_video(self.cs_conns['video'][0],self.cs_conns['video'][1])



    async def switch_p2p_server(self):
        # self.conf_server_addr['message'] = (
        #         self.conference_info['conference_ip'], self.conference_info['conference_message_port'])
        if self.is_p2p==False:
            self.is_p2p=True
            await self.close_p2p()
            await self.check_p2p()
            if(self.is_p2p==False):
                return
            message_ip=self.conns['message'][1].get_extra_info('socket').getsockname()[0]
            video_ip=self.conns['video'][1].get_extra_info('socket').getsockname()[0]
            reader,writer=self.conns['message']
            reader_video,writer_video=self.conns['video']
            self.p2p_message_server = await asyncio.start_server(self.p2p_message, message_ip, 0)
            message_ports = self.p2p_message_server.sockets[0].getsockname()[1]
            self.p2p_video_server = await asyncio.start_server(self.p2p_video, video_ip, 0)
            video_ports = self.p2p_video_server.sockets[0].getsockname()[1]

            request_data={
                    "sender":self.username,
                    "message":"p2p",
                    "ip": message_ip,
                    "message_ports": message_ports,
                    "video_ports": video_ports
                }
            request=json.dumps(request_data)
            writer.write(request.encode('utf-8'))
            await writer.drain()

            

            # self.start_server_in_thread()
            # async with self.p2p_message_server:
            #     await  self.p2p_message_server.serve_forever() 
            
        else:
            self.is_p2p=False
            await self.send_message("change CS")
            self.conns['message'] = self.cs_conns['message']
            self.conns['video'] = self.cs_conns['video']
            await self.send_video(self.p2p_conns['video'][0],self.p2p_conns['video'][1])
    
    async def close_p2p(self):
        if('message' in self.p2p_conns):
            self.p2p_conns['message'][1].close()
            await self.p2p_conns['message'][1].wait_closed()  
            del self.p2p_conns['message']
        if('video' in self.p2p_conns):  
            self.p2p_conns['video'][1].close()
            await self.p2p_conns['video'][1].wait_closed()   
            del  self.p2p_conns['video']
         
        
            

    # def start_server_in_thread(self):
    #     loop = asyncio.new_event_loop()
    #     t = threading.Thread(target=self.run_server, args=(loop,))
    #     t.start()

    # def run_server(self, loop):
    #     asyncio.set_event_loop(loop)
    #     loop.run_until_complete(self.p2p_message_server)
    #     loop.run_forever()    

    async def switch_p2p_client(self,ip=None,message_port=None,video_port=None):
        if(self.is_p2p==False):
            await self.close_p2p()
            self.is_p2p=True
            await self.send_message("P2P success")
            
            if 'video' not in self.p2p_conns:
                self.p2p_conns['video']=await asyncio.open_connection(ip,video_port)
            if 'message' not in self.p2p_conns:
                self.p2p_conns['message'] = await asyncio.open_connection(ip,message_port)
            self.conns['message'] = self.p2p_conns['message']
            self.conns['video'] = self.p2p_conns['video']

            self.p2p_video_server=None
            self.p2p_message_server=None

            await self.send_video(self.cs_conns['video'][0],self.cs_conns['video'][1])
        else:
            self.is_p2p=False
            await self.send_message("CS success")
            self.conns['message'] = self.cs_conns['message']
            self.conns['video'] = self.cs_conns['video']
            await self.send_video(self.p2p_conns['video'][0],self.p2p_conns['video'][1])
        

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



if __name__ == '__main__':
    client1 = ConferenceClient((SERVER_IP, MAIN_SERVER_PORT))
    client1.start()