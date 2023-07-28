import RPi.GPIO as gpio
from time import sleep
from queue import Queue
import threading
import sys

ENTRY="11111111"
EXIT="10000001"

PACKET_SIZE=80 # 80bytes   later 1024bytes?
HEADER_LENGTH=37 #37bytes
PAYLOAD_SIZE=PACKET_SIZE-HEADER_LENGTH

def str_to_bin(s):
        b=""
        for c in s:
                b+=bin(ord(c))[2:].zfill(8)
        return(b)

def bin_to_str(b):
        s=""
        c=1
        tmp=""
        for sig in b:
                tmp+=str(sig)
                if c==8:
                        c=0
                        s+=chr(int(tmp, 2))
                        tmp="" 
                c+=1
        return(s)

def int_to_bin(i, pad_size=8):
    return(bin(int(i))[2:].zfill(pad_size))

def bin_to_int(b, pad_size=8):
    tmp=""
    for o in b:
        if len(tmp)==pad_size:
            yield(int(tmp, 2))
            tmp=""
        tmp+=o
    yield(int(tmp, 2))

def bin_to_bytes(b, pad_size=8):
    tmp=""
    for o in b:
        if len(tmp)==pad_size:
            yield(int(tmp, 2).to_bytes(1, byteorder='big', signed=True)) 
            tmp=""
        tmp+=o
    yield(int(tmp, 2).to_bytes(1, byteorder='big', signed=True))
    

def chunks(data, size):
    tmp=""
    for o in data:
        if len(tmp) == size:
            yield(tmp)
            tmp=""
        else:
            tmp+=o
    yield tmp.zfill(size)

def checksum(data, text=True):
    return(sum(bin_to_int(data)))


gpio.setmode(gpio.BCM)



class tx:
    def __init__(self, tx_pin, target="", repeat=10, time_of_oscilation=0.2):
        self.tx_pin = tx_pin
        gpio.setup(tx_pin, gpio.OUT)
        self.target = target
        self.too=time_of_oscilation
        self.q=Queue()
        self.repeat = repeat
        self.worker=threading.Thread(target=self.watch_queue)
        self.worker.start()

    def watch_queue(self):
        seq=1
        while True:
            data, raw=self.q.get()
            if raw:
                flag=0
            elif not raw:
                flag=1
            if data!="":
                if seq==4096:
                    seq=1
                for i in range(self.repeat):
                    self.transmit_(data, self.target, seq, flag)
                seq+=1

    def tbit_(self, sig):
        if sig==0:
                gpio.output(self.tx_pin, 0)
                sleep(self.too)
        elif sig==1:
            gpio.output(self.tx_pin, 1)
            sleep(self.too)

    def transmit_(self, data, target, seq=None, flag=None, header=False):
        target=str_to_bin(target)
        if not header:
            #header: 4bytes+16bytes+16bytes+1byte
            #target: str_to_bin(zero/pi4b)
            flag=0 # is text/is frame
            h = str_to_bin(target)+int_to_bin(seq, 16)+int_to_bin(checksum(data), 16)+int_to_bin(flag)
            if len(h)!=HEADER_LENGTH*8: print("header length doesnt match constant: {}!={}".format(len(h), HEADER_LENGTH*8))
            for sig in ENTRY:
                self.tbit_(sig)
            self.transmit_(h, target, header=True)
        for sig in data:
            self.tbit_(sig)
        if not header:
            for sig in EXIT:
                self.tbit_(sig)

    def send(self, data, raw=False):
        if not raw:
            data=str_to_bin(data)
        for c in chunks(data, PAYLOAD_SIZE*8):
            if len(c)!=PAYLOAD_SIZE*8: print("payload size doesnt match constant: {}!={}".format(len(c), PAYLOAD_SIZE*8))
            self.q.put((c, raw))

    def cleanup(self):
        del self.worker
        gpio.cleanup()
        del self

class rx:
    def __init__(self,rx_pin,name, repeat=10, delay=0.1, time_of_oscilation=0.2):
        self.rx_pin = rx_pin
        gpio.setup(self.rx_pin, gpio.IN)
        self.delay=delay
        self.repeat = repeat
        self.name=name #needed to read only packets addressed to this receiver
        self.q=Queue()
        self.worker1=threading.Thread(target=self.fill_queue)
        self.worker1.start()
        self.worker2=threading.Thread(target=self.watch_queue)
        self.worker2.start()
        self.packets=Queue()

    def normalize(self, b):
        return(b[::2])

    def fill_queue(self):
        b=""
        while True:
            b+=str(gpio.input(self.rx_pin))
            sleep(self.delay)
            if EXIT in self.normalize(b):
                self.q.put(b[b.find(ENTRY)+8:b.find(EXIT)+8])
                b=b.replace(b[b.find(ENTRY)+8:b.find(EXIT)+8], "")


    def get_header(self, packet):
        try:
            h=packet[:HEADER_LENGTH*8]
            header={"target":bin_to_str(h[:4*8]), "seq":bin_to_int(h[4*8:4*8+16*8]), "checksum":bin_to_int(h[4*8+16*8:4*8+16*8+16*8]), "flag":bin_to_int(h[4*8+16*8+16*8:4*8+16*8+16*8+8])}
        except:
            return(False)# header corrupted
        return(header)

    def get_payload(packet, header):
        if not header:
            return(Fasle)# header corrupted
        p=packet[HEADER_LENGTH*8:]
        if checksum(p)==header["checksum"]:
            return(False) # payload corrupted
        else:
            if header["flag"]==1: #is text
                return(bin_to_str(p))
            elif header["flag"]==0:
                return(bin_to_bytes(p))

    def sort(self, packets):
        return(sorted(packets))


    def watch_queue(self):
        seqs=[]
        tmp=[]
        max_p=self.repeat*2
        while True:
            p=self.q.get()
            seq=self.get_header(p)["seq"]
            if seq and seq not in seqs:
                if self.get_payload(p, self.get_header(p)):
                    packets.put(p)
                    seqs.append(seq)
                    if seq==4095:
                        seqs=[]


    def recv(self):
        while True:
            p=self.packets.get()
            yield (self.get_header(p), self.get_header(p))

    def cleanup(self):
        del self.worker1
        del self.worker2
        gpio.cleanup()
        del self
