from __future__ import annotations

import argparse
import asyncio
import logging
from multiprocessing import Process
from multiprocessing import Queue

import pygame
from farm_ng.canbus import canbus_pb2
from farm_ng.canbus.canbus_client import CanbusClient
from farm_ng.service.service_client import ClientConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogitechController:
    def __init__(self, device_id: int = 0) -> None:
        # Initialize the Logitech controller.
        self.command_queue = Queue(maxsize=10)
        self.process = Process(target=self.loop_pygame, args=(device_id, self.command_queue))
        self.process.start()

    def loop_pygame(self, device_id: int, queue: Queue) -> None:
        pygame.init()
        clock = pygame.time.Clock()
        assert pygame.joystick.get_count() > 0, "No joysticks detected"

        joystick = pygame.joystick.Joystick(device_id)
        joystick.init()

        logger.info(f"Detected joystick {joystick.get_name()}")
        while True:
            for _ in pygame.event.get():
                pass

            axis_linear: float = joystick.get_axis(1)
            axis_angular: float = joystick.get_axis(3)

            twist_command = canbus_pb2.Twist2d(
                linear_velocity_x=axis_linear,
                linear_velocity_y=0.0,
                angular_velocity=axis_angular,
            )

            queue.put(twist_command)
            clock.tick(60)

class LogitechToCustomConverter:
    def __init__(self, logitech_controller):
        self.logitech_controller = logitech_controller

    def convert(self, logitech_twist):
        # Convert Logitech twist commands to your custom format.
        # Adjust this logic as needed for your specific requirements.
        custom_twist = logitech_twist  # You can modify this line to adapt to your custom format.
        return custom_twist

class CustomControllerClient:
    def __init__(self, host: str, port: int) -> None:
        self.logitech_controller = LogitechController()
        self.custom_converter = LogitechToCustomConverter(self.logitech_controller)
        self.canbus_client = CanbusClient(ClientConfig(address=host, port=port)

    async def request_generator(self) -> iter[canbus_pb2.SendVehicleTwistCommandRequest]:
        while True:
            logitech_twist: canbus_pb2.Twist2d = self.logitech_controller.command_queue.get()
            custom_twist = self.custom_converter.convert(logitech_twist)
            yield canbus_pb2.SendVehicleTwistCommandRequest(command=custom_twist)

    async def run(self) -> None:
        stream = self.canbus_client.stub.sendVehicleTwistCommand(self.request_generator())
        custom_twist_state: canbus_pb2.Twist2d
        async for custom_twist_state in stream:
            # Process custom twist state as needed.
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="custom-controller-client")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=50060)
    args = parser.parse_args()

    controller_client = CustomControllerClient(args.host, args.port)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(controller_client.run())
    except KeyboardInterrupt:
        logger.info("Exiting by KeyboardInterrupt ...")
    finally:
        loop.close()

