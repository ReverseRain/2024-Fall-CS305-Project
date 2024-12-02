import asyncio
from util import *
from config import *
import json
import uuid
import random


class ConferenceServer:
    def __init__(self, ip):
        # async server
        self.conference_server=None
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ip = ip
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = []  #维护所有在会议中的client
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """
    async def handle_video(self,):
        pass

    async def handle_audio(self,):
        pass

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
            


    
    async def broadcast_message(self, message, sender_writer):
        """
        广播文本消息给所有客户端，除了发送者
        """
        for reader,writer in self.client_conns:
            if writer != sender_writer:
                try:
                    writer.write(message.encode())
                    await writer.drain()
                except Exception as e:
                    print(f"[Error]: Failed to send message to client: {e}")
            
                

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info('peername')
        print(f"[ConferenceServer]: New client connected from {addr}")

        # 添加客户端连接到会议
        self.client_conns.append((reader,writer))

        try:
            # 为不同的数据类型创建异步任务来处理
            message_task = asyncio.create_task(self.handle_message(reader, writer))
            
            # # 这里创建任务来处理视频和音频流的接收
            # video_task = asyncio.create_task(self.handle_video_audio_stream('screen'))
            # audio_task = asyncio.create_task(self.handle_video_audio_stream('audio'))

            # 等待任务执行并并行处理
            await asyncio.gather(message_task)

        except Exception as e:
            print(f"[Error]: Error while handling client: {e}")
        finally:
            # 客户端断开时移除连接
            print(f"[ConferenceServer]: Client disconnected from {addr}")
            self.client_conns.remove((reader,writer))
            writer.close()
            await writer.wait_closed()
        



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
            
            self.conference_server = await asyncio.start_server(self.handle_client, self.conf_serve_ip, 0)
            self.conf_serve_ports = self.conference_server.sockets[0].getsockname()[1]
            
            print(f"[ConferenceServer]: Starting server at {self.conf_serve_ip}:{self.conf_serve_ports}")
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


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {} # self.conference_servers[conference_id] = ConferenceManager

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
            # 构造响应数据
            response_data = {
                "status": "success",
                "conference_info": {
                    "conference_id": conference_id,
                    "conference_ip": self.server_ip,
                    "conference_message_port": new_conference_server.conf_serve_ports
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

    async def handle_join_conference(self,reader, writer, conference_id):
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
                    "conference_message_port": self.conference_servers[conference_id].conf_serve_ports
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
                
                conference_server.cancel_conference() #这里关闭自定义的conf_server
                
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
                    await self.handle_join_conference(reader, writer,conference_id)
                elif request.startswith("quit_conference"):
                    _, conference_id = request.split()
                    await self.handle_quit_conference(reader, writer,conference_id)
                elif request.startswith("cancel_conference"):
                    _, conference_id = request.split()
                    await self.handle_cancel_conference(reader, writer,conference_id)
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
