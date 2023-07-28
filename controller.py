from transceiver import *
import signal
import sys

transmitter=tx(17, "pi4b")

def signal_handler(sig, frame):
    print("exiting...")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
    print("possible commands: up/down/left/right/stop/exit\n")
    while True:
        transmitter.send(input("enter command: "))


if __name__ == '__main__':
    main()