from transceiver import *
import cv2

transmitter=tx(17, "pi4b")
receiver=rx(27, "zero")

def stop():
    pass
def up():
    pass
def down():
    pass
def left():
    pass
def right():
    pass


def send_video():
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        while True:
            ret, frame = vidcap.read()
            data=cv2.imencode('.jpg', frame)[1].tobytes()
            b=""
            for x in data:
                b+=int_to_bin(int.from_bytes(x, byteorder='big', signed=True))
            transmitter.send(data,raw=True)
    else:
        print("camera not found!")


def controll():
    while True:
        h, data=receiver.recv()
        if "exit" in data:
            return(0)
        if "stop" in data:
            stop()
        elif "up" in data:
            up()
        elif "down" in data:
            down()
        elif "left" in data:
            left()
        elif "right" in data:
            right()

def main():
    video_t=threading.Thread(target=send_video)
    video_t.start()
    controll_t=threading.Thread(target=controll)
    controll_t.start()
    controll_t.join()
    print("exiting...")
    del video_t
    transmitter.cleanup()
    receiver.cleanup()

if __name__ == "__main__":
    main()