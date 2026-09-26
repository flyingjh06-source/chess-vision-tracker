import socketio
import asyncio

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("Connected to server")
    await sio.emit('create_room')

@sio.event
async def room_created(data):
    print(f"Room created: {data}")
    await sio.disconnect()

async def main():
    try:
        await sio.connect('https://chess-vision-tracker.onrender.com')
        await sio.wait()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == '__main__':
    asyncio.run(main())
