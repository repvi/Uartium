#!/usr/bin/env python3
"""
Uartium — UART Monitor
=======================

Launch the application:
    python main.py              # demo mode (fake messages, no hardware)
    python main.py --port COM3  # real serial port
    python main.py --port /dev/ttyUSB0 --baud 9600

Press **Start** in the GUI to begin streaming.
"""

import argparse
import sys

from uartium.gui import UartiumApp
from uartium.serial_backend import DemoSerialBackend, SerialBackend


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uartium",
        description="Uartium — UART serial monitor with colour-coded log and timeline",
    )
    parser.add_argument(
        "--port", "-p",
        default=None,
        help="Serial port (e.g. COM3, /dev/ttyUSB0).  Omit for demo mode.",
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=115200,
        help="Baud rate (default: 115200).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Demo mode: average seconds between fake messages (default: 0.5).",
    )
    args = parser.parse_args()

    if args.port:
        print(f"[Uartium] Using serial port {args.port} @ {args.baud} baud")
        backend = SerialBackend(port=args.port, baudrate=args.baud)
    else:
        print("[Uartium] No --port given → running in DEMO mode (fake messages)")
        backend = DemoSerialBackend(interval=args.interval)

    app = UartiumApp(backend=backend)
    app.build()
    app.run()


if __name__ == "__main__":
    main()
