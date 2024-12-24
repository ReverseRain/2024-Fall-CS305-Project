import asyncio

from util import *
import struct

CHUNK_SIZE = 6400
class EchoUDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_response):
        self.on_response = on_response
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode()
        print(f"Received response: {message} from {addr}")
        # 调用回调函数处理响应
        self.on_response(message)

    def error_received(self, exc):
        print(f"Error received: {exc}")
        self.transport.close()

class UDPClient:
    def __init__(self, loop, on_response):
        self.loop = loop
        self.on_response = on_response
        self.transport = None
        self.protocol = None

    async def connect(self):
        # 只在客户端启动时建立一次连接
        connect = self.loop.create_datagram_endpoint(
            lambda: EchoUDPClientProtocol(self.on_response),
            remote_addr=('127.0.0.1', 8888)
        )
        self.transport, self.protocol = await connect
        print("Connected to the server.")

    def send_message(self, message):
        if self.transport:
            # 发送消息
            self.transport.sendto(message.encode())
            print(f"Sent message: {message}")
        else:
            print("Client is not connected.")

    async def send_video(self):
        try:
            if self.transport is None:
                print("[Error]: Transport is not initialized.")
                return

            while True:
                # 捕获和压缩屏幕截图
                screen_frame = capture_screen()
                compressed_screen = compress_image(screen_frame, format='JPEG', quality=85)

                # camera_frame = capture_camera()
                # compressed_screen = compress_image(camera_frame, format='JPEG', quality=85)

                total_size = len(compressed_screen)
                num_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE

                header = struct.pack('I', num_chunks)
                self.transport.sendto(header)
                print(f"Sent header with total chunks: {num_chunks}")

                # 逐块发送图像数据
                for i in range(num_chunks):
                    start = i * CHUNK_SIZE
                    end = min((i + 1) * CHUNK_SIZE, total_size)
                    chunk = compressed_screen[start:end]

                    # 包装数据块：块序号（4字节） + 数据
                    chunk_data = struct.pack('I', i) + chunk
                    self.transport.sendto(chunk_data)

                    print(f"Sent chunk {i + 1}/{num_chunks} ({len(chunk)} bytes)")
                    await asyncio.sleep(0.1)  # 小延迟避免网络阻塞

                # 控制发送频率
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[Error]: Failed to send video. Error: {e}")
        

    async def close(self):
        if self.transport:
            self.transport.close()
            print("Connection closed.")

async def main():
    def on_response(response):
        print(f"Server echoed back: {response}")
    
    print("UDP Client Started. Type 'exit' to quit.")
    
    loop = asyncio.get_running_loop()
    client = UDPClient(loop, on_response)
    
    # 连接到服务器
    await client.connect()
    await client.send_video()
    
    # while True:
    #     # 用户输入消息
    #     message = input("Enter message to send: ")
        
    #     if message.lower() == "exit":
    #         print("Exiting client.")
    #         await client.close()  # 退出时关闭连接
    #         break  # 退出循环

    #     # client.send_message(message)  # 发送消息
        

if __name__ == '__main__':
    asyncio.run(main())
