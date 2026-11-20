# File        : code.py
# Author      : Travis Nagle (drafted with AI assistance, Anthropic Claude)
# Revision    : 1, 2026-11-02
# Project     : ECEN 5613 final project, KB2040 USB-MIDI bridge (A2)
# Description : Passes bytes both ways, unchanged, between the 8051's UART and
#               the KB2040's class-compliant USB-MIDI port, so Reaper sees the
#               8051's MIDI stream. Copy to the CIRCUITPY drive as code.py.
#                 8051 P3.1 TXD -> A3 HV1/LV1 -> KB2040 D1 (RX)
#                 KB2040 D0 (TX) -> A3 LV2/HV2 -> JP_RX pin 1 -> 8051 P3.0 RXD
#               KB2040 pins are 3.3 V only: always go through A3.
# Status      : DRAFTED, not yet run on hardware
# Leveraged   : CircuitPython usb_midi and busio.UART documentation
#               (docs.circuitpython.org)

import board
import busio
import usb_midi

# OPEN #4 (Hardware_Map section 9): 31,250-baud raw MIDI is the listed default.
# 115,200-baud packets would need framing code here and on the 8051.
BAUD = 31250

uart = busio.UART(board.TX, board.RX, baudrate=BAUD, timeout=0,
                  receiver_buffer_size=256)
usb_in = usb_midi.ports[0]    # from Reaper
usb_out = usb_midi.ports[1]   # to Reaper

while True:
    data = uart.read(64)      # None when nothing is waiting (timeout=0)
    if data:
        usb_out.write(data)
    data = usb_in.read(64)
    if data:
        uart.write(data)
