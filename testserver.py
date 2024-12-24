import asyncio
import cv2
import numpy as np
import struct
from util import *

class EchoUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.received_chunks = {}  # 用于存储接收到的块
        self.total_chunks = 0

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


async def run_server():
    print("Starting UDP server")
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: EchoUDPProtocol(),
        local_addr=('127.0.0.1', 8888)
    )

    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    finally:
        transport.close()

if __name__ == '__main__':
    asyncio.run(run_server())
