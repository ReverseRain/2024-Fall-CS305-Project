import asyncio

from util import *
from config import *
import json
import uuid
import random
import struct


class ConferenceServer:
    def __init__(self, ip):
        # async server
        self.conference_server = None
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ip = ip
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = []  # 维护所有在会议中的client
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode

        self.video_server = None

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_audio(self, reader, writer, addr):
        """
        addr: ('ip', port)
        todo
        """
        # data=await reader.read(1024)
        # while data:
        #     await self.broadcast_audio(data, addr)
        #     data = await reader.read(1024)
        addr = writer.get_extra_info('peername')
        print(f"[ConferenceServer]: Audio data received from {addr}")

        while True:
            try:
                # 接收音频数据
                data = await reader.read(1024)
                if not data:
                    break  # 如果没有数据，退出循环
                print(f"[ConferenceServer]: Audio data received: {len(data)} bytes")

                # 将接收到的数据转发给其他客户端
                for client_conn in self.client_conns:
                    if client_conn != writer:  # 不发给自己
                        client_conn.write(data)
                        await client_conn.drain()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ConferenceServer]: Error while handling audio: {e}")
                break

        # 关闭连接
        print(f"[ConferenceServer]: Closing audio connection from {addr}")
        self.client_conns.remove(writer)
        writer.close()
        await writer.wait_closed()

    async def handle_message(self, reader, writer):
        """
        tcp连接处理文本类型消息 在 self.conf_serve_ports上处理
        """
        try:
            while True:

                data = await reader.read(1024)
                if not data:
                    break  # 如果没有接收到数据，退出循环

                message = data.decode()
                print(f"[ConferenceServer-{self.conference_id}]: Received message: {message}")
                # response='Received'
                # writer.write(response.encode('utf-8'))
                # await writer.drain()

                # 处理完消息后，广播给其他客户端
                await self.broadcast_message(message, writer)

        except Exception as e:
            print(f"[Error]: Failed to handle message. Error: {e}")

        finally:
            print(f"[ConferenceServer-{self.conference_id}]: Closing connection.")
            writer.close()
            await writer.wait_closed()

    async def handle_video(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        window_name = f"Client-{client_addr}"
        try:
            while True:
                length_data = await reader.readexactly(4)
                frame_length = int.from_bytes(length_data, 'big')

                print(f"[{window_name}] Expected frame length: {frame_length}")

                if frame_length == 0:
                    print(f"[{window_name}]: Received stop signal. Closing display.")
                    cv2.destroyWindow(window_name)
                    continue

                # 确保读取到完整的帧数据
                data = await reader.readexactly(frame_length)
                frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is None:
                    print(f"[{window_name}]: Failed to decode frame.")
                    continue

                cv2.imshow(window_name, frame)
                cv2.waitKey(1)

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

    async def broadcast_audio(self, audio, addr):
        for client in self.client_conns:
            if client.get_extra_info('sockname') == addr:
                continue
            client[1].write(audio)
            await client[1].drain()
            # client.sendto(audio, client.get_extra_info('sockname'))

    async def broadcast_video(self, frame, sock):

        # 遍历所有客户端连接
        for port in self.data_serve_ports:
            if port != sock.sockets[0].getsockname()[1]:
                try:
                    # 压缩视频帧并发送
                    compressed_frame = compress_image(frame, format='JPEG', quality=85)
                    sock.sendto(compressed_frame, self.conf_serve_ip)
                except Exception as e:
                    print(f"[Error]: Failed to send frame to client: {e}")

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info('peername')
        print(f"[ConferenceServer]: New client connected from {addr}")

        # 添加客户端连接到会议
        self.client_conns.append((reader, writer))

        try:
            # 为不同的数据类型创建异步任务来处理
            # message_task = asyncio.create_task(self.handle_message(reader, writer))
            # video_task = asyncio.create_task(self.handle_video(reader, writer))
            # # 这里创建任务来处理视频和音频流的接收
            # video_task = asyncio.create_task(self.handle_video_audio_stream('screen'))
            # video_task = asyncio.create_task(self.handle_video(self.video_server))
            # audio_task = asyncio.create_task(self.handle_video_audio_stream('audio'))
            # audio_task = asyncio.create_task(self.handle_audio(reader,writer,addr))

            # 等待任务执行并并行处理
            # await asyncio.gather(message_task, audio_task)
            while True:
                data = await reader.read(100)
                if not data:
                    break
                # 处理客户端请求，包含音频传输等
                if data == b'audio':
                    await self.handle_audio(reader, writer)

        except Exception as e:
            print(f"[Error]: Error while handling client: {e}")
        finally:
            # 客户端断开时移除连接
            print(f"[ConferenceServer]: Client disconnected from {addr}")
            self.client_conns.remove((reader, writer))
            writer.close()
            await writer.wait_closed()

    async def receive_text(self, reader, writer):
        text_message = await reader.read(1024)  # 假设消息不超过1024字节

        reader.close()
        return text_message.decode()  # 解码为字符串

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """

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

            # audio udp
            ############## TODO 这里有问题，无法创建会议 ############################

            # audio_server = await asyncio.get_running_loop().create_datagram_endpoint(
            #     lambda: AudioUDPProtocol(self),
            #     local_addr=(self.conf_serve_ip, 12345)
            # )
            # transport, protocol = await audio_server
            # self.data_serve_ports['audio'] = transport.get_extra_info('sockname')[1]

            #######################################################
            self.video_server = await asyncio.start_server(self.handle_video, self.conf_serve_ip, 0)
            self.data_serve_ports['video'] = self.video_server.sockets[0].getsockname()[1]

            print(f"[ConferenceServer]: Starting main server at {self.conf_serve_ip}:{self.conf_serve_ports}")
            print(f"[ConferenceServer]: Starting video server at {self.conf_serve_ip}:{self.data_serve_ports['video']}")
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


# UDP audio
class AudioUDPProtocol:
    def __init__(self, server):
        self.server = server
# 8 3 6 9 / 9  38  6
    def datagram_received(self, data, addr):
        asyncio.create_task(self.server.handle_audio(data, addr))

    def connection_made(self, transport):
        """
        Called when the connection is established.
        """
        self.transport = transport
        print(f"Connection established to {transport.get_extra_info('peername')}")

# udp 处理视频
class EchoUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, server):
        self.transport = None
        self.received_chunks = {}  # 用于存储接收到的块
        self.total_chunks = 0
        self.main_server = server

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print('Received a chunk from', addr)

        # 如果还没有接收到文件头，先接收文件头
        if self.total_chunks == 0:
            # 文件头包含总块数，4字节
            self.total_chunks = struct.unpack('I', data)[0]
            print(f"Received header: total chunks = {self.total_chunks}")
            return  # 文件头接收完后返回，等待后续的块数据

        # 获取块序号（4字节）和数据块
        chunk_id = struct.unpack('I', data[:4])[0]
        chunk_data = data[4:]

        # 存储接收到的数据块
        self.received_chunks[chunk_id] = chunk_data

        print(f"Received chunk {chunk_id + 1}/{self.total_chunks} ({len(chunk_data)} bytes)")

        # 如果所有块都已经收到，进行重组
        if len(self.received_chunks) == self.total_chunks:
            asyncio.get_event_loop().run_in_executor(None, self.handle_data)

            # 重置状态，为下一个图像准备

    def handle_data(self):
        # 将所有块按序号排序并合并
        print(f'handle data total_chunks= {self.total_chunks}')

        all_data = b''.join([self.received_chunks[i] for i in range(self.total_chunks)])

        # 使用 OpenCV 解码图像
        frame = cv2.imdecode(np.frombuffer(all_data, dtype=np.uint8), cv2.IMREAD_COLOR)

        if frame is None:
            print("Failed to decode frame.")
        else:
            cv2.imshow('Received Frame', frame)
            cv2.waitKey(1)
        self.received_chunks.clear()
        self.total_chunks = 0


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
            print('here')

            await new_conference_server.wait_for_port_assignment()
            # print(new_conference_server.data_serve_ports['video'])
            # 构造响应数据
            response_data = {
                "status": "success",
                "conference_info": {
                    "conference_id": conference_id,
                    "conference_ip": self.server_ip,
                    "conference_message_port": new_conference_server.conf_serve_ports,
                    "conference_video_port": new_conference_server.data_serve_ports['video']
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
                        "conference_video_port": self.conference_servers[conference_id].data_serve_ports['video']
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

                conference_server.cancel_conference()  # 这里关闭自定义的conf_server

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
