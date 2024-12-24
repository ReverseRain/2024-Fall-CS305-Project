import asyncio

from util import *
from config import *
import json
import uuid
import random
import struct
import wave

class ConferenceServer:
    def __init__(self, ip):
        # async server
        self.conference_server = None
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ip = ip
        self.conf_serve_ports = None
        self.data_serve_ports = {'video':9001, 'audio':9002}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = []  # 维护所有在会议中的client
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode

        self.video_server=None
        self.audio_server=None
        self.video_client_conns=[]
        self.audio_client_conns=[]
        self.audio_transport = None
        self.audio_protocol = None

        self.p2p_message_ip = None
        self.p2p_message_port = None

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_audio(self, client_addr, wf, data, addr):
        wf.writeframes(data)
        """接收来自客户端的音频数据并广播"""
        # print(f"[ConferenceServer]: Received audio data from {addr}, forwarding to other clients.")
        # 广播接收到的音频数据
        await self.broadcast_audio(data, addr)

    # async def handle_audio(self, reader, writer):
    #     self.audio_client_conns.append((reader,writer))
    #
    #     # data=await reader.read(1024)
    #     # while data:
    #     #     await self.broadcast_audio(data, addr)
    #     #     data = await reader.read(1024)
    #     addr = writer.get_extra_info('peername')
    #     print(f"[ConferenceServer]: Audio data receiving from {addr}")
    #
    #
    #     try:
    #         while True:
    #             # 接收音频数据
    #             data = await reader.readexactly(2048)
    #             if not data:
    #                 break  # 如果没有数据，退出循环
    #             print(f"[ConferenceServer]: Audio data received: {len(data)} bytes")
    #             await self.broadcast_audio(data,writer)
    #
    #     except asyncio.IncompleteReadError:
    #         print(f"Client disconnected abruptly.")
    #     except Exception as e:
    #         print(f"[ConferenceServer]: Error while handling audio: {e}")
    #     finally:
    #
    #         # 关闭连接
    #         print(f"[ConferenceServer]: Closing audio connection from {addr}")
    #         writer.close()
    #         await writer.wait_closed()

    async def handle_message(self, reader, writer):
        """
        tcp连接处理文本类型消息 在 self.conf_serve_ports上处理
        """
        try:
            while True:

                data = await reader.read(1024)
                if not data:
                    break  # 如果没有接收到数据，退出循环

                message = json.loads(data.decode('utf-8'))
                print(f"[ConferenceServer-{self.conference_id}]: Received message: {message}")
                # response='Received'
                # writer.write(response.encode('utf-8'))
                # await writer.drain()
                print(message.get("message"))
                if (message.get("message") == 'quit'):
                    index = self.client_conns.index((reader, writer))

                    reader_video, writer_video = self.video_client_conns[index]
                    writer_video.close()
                    await writer_video.wait_closed()
                    del self.client_conns[index]
                    del self.video_client_conns[index]
                    continue
                elif (message.get("message") == 'p2p'):
                    print(len(self.client_conns))
                    if (len(self.client_conns) != 2):
                        response = {
                            "sender": "server",
                            "message": "No"
                        }
                        writer.write(json.dumps(response).encode('utf-8'))
                        await writer.drain()
                        continue
                    else:
                        self.mode = 'p2p'
                        data = await reader.read(1024)
                        if not data:
                            break
                        message = data.decode()
                        for reader2, writer2 in self.client_conns:
                            if (writer2 != writer):
                                writer2.write(message.encode('utf-8'))
                                await writer.drain()

                        message_data = json.loads(data.decode('utf-8'))
                        self.p2p_message_ip = message_data.get("ip")
                        self.p2p_message_port = message_data.get("message_ports")
                        continue
                elif (message.get("message") == "new mode message start"):
                    writer.write(data)
                    await writer.drain()
                elif (message.get("message") == 'change CS'):
                    self.mode = 'Client-Server'
                    self.p2p_message_ip = None
                    self.p2p_message_ip = None

                # 处理完消息后，广播给其他客户端
                await self.broadcast_message(data.decode(), writer)

        except Exception as e:
            print(f"[Error]: Failed to handle message. Error: {e}")

        finally:
            print(f"[ConferenceServer-{self.conference_id}]: Closing connection.")
            writer.close()
            await writer.wait_closed()

    async def handle_video(self, reader, writer):
        self.video_client_conns.append((reader, writer))

        # if(len(self.video_client_conns)==3 and self.mode=='p2p'):
        #     address_length=0
        #     total_length =  4 + 4 + address_length
        #     #4byte 地址长度 + 4byte 数据帧长度 + 地址
        #     address_length_bytes=address_length.to_bytes(4,'big')
        #     total_length_bytes = total_length.to_bytes(4, 'big')
        #     frame_length_bytes=(0).to_bytes(4,'big')

        #     packet=total_length_bytes + address_length_bytes +frame_length_bytes

        #     await self.broadcast_video(packet,writer)

        client_addr = writer.get_extra_info('peername')
        print(f"Client-{client_addr}")
        window_name = f"Client-{client_addr}"
        try:
            total_chunks = 0
            received_chunks = {}
            while True:
                length_data = await reader.readexactly(4)
                receive_len = int.from_bytes(length_data, 'big')

                print(f"[{window_name}] Expected frame length: {receive_len}")

                # if frame_length==0:
                #     print(f"[{window_name}]: Received stop signal. Closing display.")
                #     cv2.destroyWindow(window_name)
                #     continue

                # 确保读取到完整的帧数据
                data = await reader.readexactly(receive_len)
                packet = length_data + data
                await self.broadcast_video(packet, writer)
                # frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8),cv2.IMREAD_COLOR)

                # if frame is None:
                #     print(f"[{window_name}]: Failed to decode frame.")
                #     continue
                # cv2.imshow(window_name, frame)
                # cv2.waitKey(1)

                # await self.broadcast_video(frame, sock)
        except asyncio.IncompleteReadError:
            print(f"[{window_name}]: Client disconnected abruptly.")
        except Exception as e:
            print(f"[Error]: Failed to handle video for {window_name}. Error: {e}")
            cv2.destroyAllWindows()

        finally:
            print(f"[ConferenceServer-{self.conference_id}]: Closing connection.")
            writer.close()
            await writer.wait_closed()
            cv2.destroyAllWindows()

    async def broadcast_message(self, message, sock):
        """
        广播文本消息给所有客户端，除了发送者
        """
        for reader, writer in self.client_conns:
            if writer != sock:
                try:
                    writer.write(message.encode())
                    await writer.drain()
                except Exception as e:
                    print(f"[Error]: Failed to send message to client: {e}")

    async def broadcast_video(self, packet, sock):

        # 遍历所有客户端连接
        if (self.mode != 'p2p'):
            for reader, writer in self.video_client_conns:
                try:
                    writer.write(packet)
                    await writer.drain()
                except Exception as e:
                    print(f"[Error]: Failed to send video to client: {e}")
        else:
            for reader, writer in self.video_client_conns:
                if (writer != sock):
                    try:
                        writer.write(packet)
                        await writer.drain()
                    except Exception as e:
                        print(f"[Error]: Failed to send video to client: {e}")

    async def quit_p2p(self, request_data):

        reader, writer = await asyncio.open_connection(self.p2p_message_ip, self.p2p_message_port)
        print('step 2')
        writer.write(request_data.encode('utf-8'))
        print('step 3')
        await writer.drain()
        print('step 4')
        # print('shuahsu')

        writer.close()
        await writer.wait_closed()

    # async def broadcast_audio(self, audio, sock):
    #     for reader, writer in self.audio_client_conns:
    #         if writer != sock:
    #             try:
    #                 writer.write(audio)
    #                 await writer.drain()
    #             except Exception as e:
    #                 print(f"[Error]: Failed to send message to client: {e}")

    async def broadcast_audio(self, audio, addr):
        """将接收到的音频数据广播给所有其他客户端"""
        print(len(self.audio_client_conns))
        try:
            for address in self.audio_client_conns:
                print(address)
                if address != addr:
                    self.audio_transport.sendto(audio, address)
                    print(address)

        except Exception as e:
            print(f"[Error]: Error broadcasting audio to {addr}: {e}")
    

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info('peername')
        print(f"[ConferenceServer]: New client connected from {addr}")

        # 添加客户端连接到会议
        self.client_conns.append((reader,writer))
        if (len(self.client_conns) != 2 and self.mode == 'p2p'):
            request_data = {
                "sender": self.conference_id,
                "message": "p2p only for 2 clients change to cs"
            }
            print('why')
            request_data = json.dumps(request_data)
            await self.quit_p2p(request_data)
            # self.mode='Client-Server'
            print('did it ?')

        try:
            # 为不同的数据类型创建异步任务来处理
            message_task = asyncio.create_task(self.handle_message(reader, writer))
            #video_task = asyncio.create_task(self.handle_video(reader, writer))
            # # 这里创建任务来处理视频和音频流的接收
            # video_task = asyncio.create_task(self.handle_video_audio_stream('screen'))
            #video_task = asyncio.create_task(self.handle_video(self.video_server))
            # audio_task = asyncio.create_task(self.handle_video_audio_stream('audio'))

            # audio_transport, audio_protocol = await self.setup_audio_server()
            # self.audio_client_conns.append((self.audio_transport, self.audio_protocol))

            # 等待任务执行并并行处理
            await asyncio.gather(message_task)

        except Exception as e:
            print(f"[Error]: Error while handling client: {e}")
        finally:
            # 客户端断开时移除连接
            print(f"[ConferenceServer]: Client disconnected from {addr}")
            if ((reader, writer) in self.client_conns):
                self.client_conns.remove((reader, writer))
            writer.close()
            await writer.wait_closed()

    async def setup_audio_server(self):
        """启动一个 UDP 服务器来处理音频数据"""
        # 创建一个 UDP 端点并返回相关的 transport 和 protocol
        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(
            lambda: AudioUDPServerProtocol(self),
            local_addr=(self.conf_serve_ip, self.data_serve_ports['audio'])
        )
        transport, protocol = await listen
        print(f"[ConferenceServer]: Audio server started on {self.conf_serve_ip}:{self.data_serve_ports['audio']}")
        return transport, protocol

    async def receive_text(self, reader, writer):
        text_message = await reader.read(1024)  # 假设消息不超过1024字节

        reader.close()
        return text_message.decode()  # 解码为字符串

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        print('len of',len(self.client_conns))
        for reader,writer in self.client_conns:
            try:
                response={
                "sender": "conf_server",
                "message": "conf close",
            }
                writer.write(json.dumps(response).encode('utf-8'))
                await writer.drain()
            except Exception as e:
                print(f"[Error]: Failed to send message to client: {e}")
        for _,(reader,writer) in enumerate(self.client_conns):
            writer.close()
            await writer.wait_closed()
        for _,(reader,writer) in enumerate(self.video_client_conns):
            writer.close()
            await writer.wait_closed()
        self.client_conns={}
        self.video_client_conns={}

    async def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''

        async def start_server():
            # main server TCP . handle request  message
            self.conference_server = await asyncio.start_server(self.handle_client, self.conf_serve_ip, 0)
            self.conf_serve_ports = self.conference_server.sockets[0].getsockname()[1]

            # 创建处理视频的udp socket
            '''
            transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: EchoUDPProtocol(self),
                local_addr=(self.conf_serve_ip, 0)
            )
            self.video_server=transport

            self.data_serve_ports['video']=transport.get_extra_info('sockname')[1]
            '''

            self.video_server = await asyncio.start_server(self.handle_video, self.conf_serve_ip, 0)
            self.data_serve_ports['video'] = self.video_server.sockets[0].getsockname()[1]

            # self.audio_server = await asyncio.start_server(self.handle_audio, self.conf_serve_ip, 0)
            # self.data_serve_ports['audio'] = self.audio_server.sockets[0].getsockname()[1]

            self.audio_transport,self.audio_protocol = await self.setup_audio_server()
            print(f"[ConferenceServer]: Starting main server at {self.conf_serve_ip}:{self.conf_serve_ports}")
            print(f"[ConferenceServer]: Starting video server at {self.conf_serve_ip}:{self.data_serve_ports['video']}")
            print(f"[ConferenceServer]: Starting audio server at {self.conf_serve_ip}:{self.data_serve_ports['audio']}")
            # Serve the server until it is stopped
            async with self.conference_server:
                await self.conference_server.serve_forever()

        await start_server()

    async def wait_for_port_assignment(self):
        """
        等待端口号分配完成
        """
        while self.conf_serve_ports is None:
            await asyncio.sleep(0.1)  # 等待端口分配，避免过多占用 CPU 时间


class AudioUDPServerProtocol(asyncio.DatagramProtocol):
    """处理UDP音频数据的协议"""

    def __init__(self, server):
        self.server = server
        self.transport = None
        self.wf = wave.open('server_output.wav', 'wb')
        self.wf.setnchannels(1)  # 设置声道数
        self.wf.setsampwidth(2)  # 设置样本宽度
        self.wf.setframerate(44100)
        self.client_addr = server.audio_client_conns
    def connection_made(self, transport):
        """UDP 连接建立"""
        self.transport = transport
        print("[AudioUDPServerProtocol]: UDP connection established.")

    def datagram_received(self, data, addr):
        if addr not in self.client_addr:
            self.client_addr.append(addr)
            print(f"add {addr}")
        try:
            # 判断是否为字符串
            message = data.decode('utf-8')  # 尝试将数据解码为 UTF-8 字符串
            print(f"Received string: {message}")
            if message == "quit":
                self.client_addr.remove(addr)
        except UnicodeDecodeError:
            asyncio.create_task(self.server.handle_audio(self.client_addr, self.wf ,data, addr))

    def error_received(self, exc):
        """处理接收错误"""
        print(f"[AudioUDPServerProtocol]: Error received: {exc}")

    def connection_lost(self, exc):
        """UDP 连接丢失"""
        print("[AudioUDPServerProtocol]: UDP connection lost.")


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager

    async def handle_creat_conference(self, reader, writer):
        """
        Create conference: create and start the corresponding ConferenceServer,
        and reply necessary info to client.
        """
        try:

            # 生成唯一的会议 ID

            conference_id = str(random.randint(10000000, 99999999))

            print(f"[Info]: Creating a new conference with ID: {conference_id}")

            # 初始化会议服务器
            new_conference_server = ConferenceServer(self.server_ip)
            new_conference_server.conference_id = conference_id
            self.conference_servers[conference_id] = new_conference_server
            asyncio.create_task(new_conference_server.start())


            await new_conference_server.wait_for_port_assignment()
            print('port',new_conference_server.data_serve_ports['video'])
            # 构造响应数据
            response_data = {
                "status": "success",
                "conference_info": {
                    "conference_id": conference_id,
                    "conference_ip": self.server_ip,
                    "conference_message_port": new_conference_server.conf_serve_ports,
                    "conference_video_port": new_conference_server.data_serve_ports['video'],
                    "conference_audio_port": new_conference_server.data_serve_ports['audio']
                    
                    # "server_ip": self.server_ip,
                    # "ports": new_conference_server.conf_serve_ports,  # Example, needs initialization
                }
            }
            writer.write(json.dumps(response_data).encode('utf-8'))
            await writer.drain()

        except Exception as e:
            # 错误响应
            error_response = {
                "status": "error",
                "message": str(e),
            }
            writer.write(json.dumps(error_response).encode('utf-8'))
            await writer.drain()
            print(f"[Error]: Failed to create conference. Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_join_conference(self, reader, writer, conference_id):
        """
        Join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        try:
            # 检查会议是否存在
            if conference_id in self.conference_servers:
                conference_server = self.conference_servers[conference_id]

                # 这里你可以返回具体的会议相关信息，例如服务器的端口，或是其他必要信息
                response_data = {
                    "status": "success",
                    "conference_info": {
                        "conference_id": conference_id,
                        "conference_ip": self.server_ip,
                        "conference_message_port": self.conference_servers[conference_id].conf_serve_ports,
                        "conference_video_port": self.conference_servers[conference_id].data_serve_ports['video'],
                        "conference_audio_port": self.conference_servers[conference_id].data_serve_ports['audio']
                        # "server_ip": self.server_ip,
                        # "ports": new_conference_server.conf_serve_ports,  # Example, needs initialization
                    }

                }
                writer.write(json.dumps(response_data).encode('utf-8'))
                await writer.drain()
                print(f"[Server]: Client joined conference {conference_id}")
            else:
                # 会议不存在的错误响应
                error_response = {
                    "status": "error",
                    "message": f"Conference {conference_id} not found.",
                }
                writer.write(json.dumps(error_response).encode('utf-8'))
                await writer.drain()
                print(f"[Server]: Failed to join conference {conference_id}. Conference not found.")
        except Exception as e:
            # 错误响应
            error_response = {
                "status": "error",
                "message": str(e),
            }
            writer.write(json.dumps(error_response).encode('utf-8'))
            await writer.drain()
            print(f"[Server]: Error while trying to join conference {conference_id}. Error: {e}")

    async def handle_quit_conference(self, reader, writer, conference_id):
        """
        quit conference (in-meeting request & or no need to request)
        """
        try:
            # 检查会议是否存在
            if conference_id in self.conference_servers:
                reader, writer = self.conference_servers[conference_id].client_conns
                writer.close()
                await writer.wait_closed()

                reader, writer = self.conference_servers[conference_id].video_client_conns
                writer.close()
                await writer.wait_closed()

                self.conference_servers[conference_id].client_conns.remove()
                self.conference_servers[conference_id].video_client_conns.remove()
                self.conference_servers[conference_id].audio_client_conns.remove()
                # 构造响应数据
                response_data = {
                    "status": "success",
                    "message": "You have left the conference."
                }
                writer.write(json.dumps(response_data).encode('utf-8'))
                await writer.drain()
            else:
                # 会议不存在的错误响应
                error_response = {
                    "status": "error",
                    "message": "Conference not found.",
                }
                writer.write(json.dumps(error_response).encode('utf-8'))
                await writer.drain()
        except Exception as e:
            # 错误响应
            error_response = {
                "status": "error",
                "message": str(e),
            }
            writer.write(json.dumps(error_response).encode('utf-8'))
            await writer.drain()
            print(f"[Error]: Failed to quit conference. Error: {e}")

    async def handle_cancel_conference(self, reader, writer, conference_id):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        try:
            if conference_id in self.conference_servers:
                conference_server = self.conference_servers[conference_id]

                await conference_server.cancel_conference()  # 这里关闭自定义的conf_server

                del self.conference_servers[conference_id]

                response_data = {
                    "status": "success",
                    "message": "Conference has been cancelled."
                }
                writer.write(json.dumps(response_data).encode('utf-8'))
                await writer.drain()
            else:
                # 会议不存在的错误响应
                error_response = {
                    "status": "error",
                    "message": "Conference not found.",
                }
                writer.write(json.dumps(error_response).encode('utf-8'))
                await writer.drain()
        except Exception as e:
            # 错误响应
            error_response = {
                "status": "error",
                "message": str(e),
            }
            writer.write(json.dumps(error_response).encode('utf-8'))
            await writer.drain()
            print(f"[Error]: Failed to cancel conference. Error: {e}")

    async def request_handler(self, reader, writer):
        """
        Handle incoming requests from clients and dispatch to the appropriate handlers.
        """
        addr = writer.get_extra_info('peername')
        print(f"[Server]: New connection from {addr}")

        try:
            while True:
                # Read the request type (assumes the client sends request type first)
                data = await reader.read(1024)
                if not data:
                    break  # Connection closed by the client

                request = data.decode().strip()
                print(f"[Server]: Request received: {request}")

                # Dispatch the request
                if request.startswith("create_conference"):
                    await self.handle_creat_conference(reader, writer)
                elif request.startswith("join_conference"):
                    _, conference_id = request.split()
                    await self.handle_join_conference(reader, writer, conference_id)
                elif request.startswith("quit_conference"):
                    _, conference_id = request.split()
                    await self.handle_quit_conference(reader, writer, conference_id)
                elif request.startswith("cancel_conference"):
                    _, conference_id = request.split()
                    await self.handle_cancel_conference(reader, writer, conference_id)
                else:
                    response = "Unknown request"
                    writer.write(response.encode())
                    await writer.drain()
                    print(f"[Server]: Sent response: {response}")
        except Exception as e:
            print(f"[Server]: Error: {e}")
        finally:
            print(f"[Server]: Closing connection with {addr}")
            writer.close()
            await writer.wait_closed()

    def start(self):
        async def start_server():
            print(f"[Server]: Starting server at {self.server_ip}:{self.server_port}")
            self.main_server = await asyncio.start_server(self.request_handler, self.server_ip, self.server_port)

            # Serve the server until it is stopped
            async with self.main_server:
                await self.main_server.serve_forever()

        asyncio.run(start_server())


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
