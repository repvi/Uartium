# Uartium — UART Serial Monitor

A lightweight UART serial monitor built with **Dear PyGui** and **PySerial**.

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)

## Features

- **Start / Stop** buttons to control the serial stream
- **Scrollable colour-coded message log**
  - 🟢 **EVENT** — green
  - 🔵 **INFO** — light blue
  - 🟡 **WARNING** — amber
  - 🔴 **ERROR** — red
  - ⚪ **DEBUG** — grey
- **Real-time timeline scatter chart** plotting every message by level over time
- **Demo mode** — runs without hardware using realistic fake UART messages

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run in demo mode (no hardware needed)
python main.py

# 4. Or connect to a real serial port
python main.py --port COM3 --baud 115200
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` / `-p` | *(none → demo)* | Serial port, e.g. `COM3` or `/dev/ttyUSB0` |
| `--baud` / `-b` | `115200` | Baud rate |
| `--interval` | `0.5` | Demo mode: avg seconds between fake messages |

## Project Structure

```
Uartium/
├── main.py                   # Entry point
├── requirements.txt          # pip dependencies
├── uartium/
│   ├── __init__.py
│   ├── serial_backend.py     # PySerial wrapper + demo mock
│   └── gui.py                # Dear PyGui interface
└── README.md
```

## Using with Real Hardware

Your device should send newline-terminated text over UART.  
Lines prefixed with a level tag are automatically colour-coded:

```
[EVENT] Sensor initialized
[INFO] Temperature: 23.4
[WARNING] Battery low
[ERROR] CRC mismatch
[DEBUG] Heap free: 34816
```

Lines without a recognised prefix default to **INFO**.
