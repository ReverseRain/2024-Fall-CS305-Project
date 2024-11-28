from util import *
import asyncio
import json
from config import *

class ConferenceClient:
    def __init__(self,server_addr):
        # sync client
        self.is_working = True
        self.server_addr =server_addr   # server addr
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_id=None

        self.conference_info = None  # you may need to save and update some conference_info regularly

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

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
                self.conference_id=self.conference_info['conference_id']
                self.show_info(f"[Success]: Conference created with ID: {self.conference_id}")
            else:
                self.show_info(f"[Error]: Failed to create conference. Reason: {response_data.get('message')}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()
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
                #self.conference_info = response_data["conference_info"]
                self.on_meeting = True
                self.conference_id = conference_id
                self.show_info(f"[Success]: Successfully joined conference with ID: {self.conference_id}")
            else:
                # 会议加入失败
                self.show_info(f"[Error]: Failed to join conference. Reason: {response_data.get('message')}")

            # 关闭连接
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.show_info(f"[Error]: Unable to join conference. Error: {e}")


    async def quit_conference(self,conference_id):
        """
        quit your on-going conference
        """
        try:
        # 初始化连接
            reader, writer = await asyncio.open_connection(self.server_addr[0], self.server_addr[1])
            self.show_info("[Info]: Connected to the server to quit the conference.")
            
            request_data = "quit_conference "+str(conference_id)
            
            writer.write(request_data.encode('utf-8'))
            await writer.drain()

            # 接收服务器响应
            response = await reader.read(1024)
            response_data = json.loads(response.decode('utf-8'))
            
            if response_data.get("status") == "success":
                self.on_meeting = False
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
            
            request_data = "cancel_conference "+str(self.conference_id)
        
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

    def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''
    
    def show_info(self,info):
        print(info)


    def start(self):
        """
        execute functions based on the command line input
        """
        while True:
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'

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
                    asyncio.run(self.quit_conference(fields[1]))
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')


if __name__ == '__main__':
    client1 = ConferenceClient((SERVER_IP,MAIN_SERVER_PORT))
    client1.start()

