import RPi.GPIO as gpio
from time import sleep, time
from queue import Queue
import threading
import sys
import os

ENTRY="1111111111111111"
EXIT="1011111111111111"

PACKET_SIZE=80 # 80bytes   later 1024bytes?
HEADER_LENGTH=9 #37bytes
PAYLOAD_SIZE=PACKET_SIZE-HEADER_LENGTH

def str_to_bin(s):
        b=""
        for c in s:
                b+=bin(ord(c))[2:].zfill(8)
        return(str(b))

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
    return(str(bin(int(i))[2:].zfill(pad_size)))

def bin_to_int(b, pad_size=8):
    if len(b)%pad_size!=0:
        yield -1
    else:
        tmp=""
        for o in b:
            if len(tmp)==pad_size:
                yield(int(tmp, 2))
                tmp=""
            tmp+=o
        if tmp !='':
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




class tx:
    def __init__(self, tx_pin, target="", repeat=10, time_of_oscilation=0.0001):
        os.nice(20)
        gpio.setmode(gpio.BCM)
        self.tx_pin = tx_pin
        gpio.setup(self.tx_pin, gpio.OUT)
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
        if not gpio.getmode(): gpio.setmode(gpio.BCM)
        gpio.setup(self.tx_pin, gpio.OUT)
        sig=int(sig)
        print(sig, flush=True, end="")
        if sig==0:
                gpio.output(self.tx_pin, 1)
                sleep(self.too)
                gpio.output(self.tx_pin, 0)
                sleep(self.too)
        elif sig==1:
            gpio.output(self.tx_pin, 1)
            sleep(self.too*4)
            gpio.output(self.tx_pin, 0)
            sleep(self.too)
        else:
            print("error in tbit")

    def transmit_(self, data, target, seq=None, flag=None, header=False):
        if not header:
            #header: 4bytes+2bytes+2bytes+1byte
            #target: str_to_bin(zero/pi4b)
            flag=1 # is text/is frame
            h = str_to_bin(target)+int_to_bin(seq, 16)+int_to_bin(checksum(data), 16)+int_to_bin(flag)
            hl={"target":str_to_bin(target), "seq":int_to_bin(seq, 16), "checksum":int_to_bin(checksum(data),16), "flag":int_to_bin(flag)}
            hlc={"target":target, "seq":seq, "checksum":checksum(data), "flag":flag}
            print("header raw:", h, "\n\n")
            print("header bin:", hl, "\n\n")
            print("header clean:", hlc, "\n\n")
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
        return(0)

    def cleanup(self):
        del self.worker
        gpio.cleanup()
        return(0)

class rx:
    def __init__(self,rx_pin,name, repeat=10,  time_of_oscilation=0.0001, tolerance=50):
        os.nice(20)
        self.rx_pin = rx_pin
        self.f=False
        self.zero_space=range(500)
        self.one_space=range(0)
        gpio.setmode(gpio.BCM)
        gpio.setup(self.rx_pin, gpio.IN)
        self.repeat = repeat
        #self.delay=time_of_oscilation/2
        self.f=int(self.calc_frequency()) #1/s
        self.one_space=range(int((self.f*(time_of_oscilation*4+time_of_oscilation)))-tolerance, int((self.f*(time_of_oscilation*4+time_of_oscilation)))+tolerance)
        self.zero_space=range(int((self.f*(time_of_oscilation*2)))-tolerance, int((self.f*(time_of_oscilation*2)))+tolerance) 
        print(self.one_space)
        print(self.zero_space)
        if int(self.f*(time_of_oscilation*4+time_of_oscilation)) not in self.one_space:
            print("you need to decrease the time_of_oscilation!")
            self.cleanup()
            return(0)
        if int(self.f*(time_of_oscilation*2)) not in self.zero_space:
            print("you need to decrease the time_of_oscilation!")
            self.cleanup()
            return(0)
        self.name=name #needed to read only packets addressed to this receiver
        self.q=Queue()
        self.worker1=threading.Thread(target=self.fill_queue)
        self.worker1.start()
        self.worker2=threading.Thread(target=self.watch_queue)
        self.worker2.start()
        self.packets=Queue()



    def calc_frequency(self):
        os.nice(20)
        b=""
        t1=time()
        for i in range(10):
            s=str(gpio.input(self.rx_pin))
            #print(s, end="", flush=True)
            b+=s
            if len(b)>PACKET_SIZE*10: b=""
            if EXIT in self.normalize(b):
                self.q.put(b[b.find(ENTRY)+16:b.find(EXIT)])
                b=""
        return(1/((time()-t1)/10))



    def normalize(self, b):
        #return(b[::2]) #removed for debugging purposes
        #return(b)
        clean=""
        sigs=" ".join((" ".join(b.split("01"))).split("10")).split()
        for i in range(0, len(sigs)):
            if "1" in sigs[i]:
                if sigs[i].count("1") in self.zero_space:
                   clean+="0"
                elif sigs[i].count("1") in self.one_space: 
                   clean+="1"
                #print("1*{}".format(sigs[i].count("1")))
        #print(clean)
        return(clean)

    def fill_queue(self):
        os.nice(20)
        b=""
        while True:
            s=str(gpio.input(self.rx_pin))
            #print(s, end="", flush=True)
            b+=s
            if EXIT in self.normalize(b):
                self.q.put(b[b.find(ENTRY)+16:b.find(EXIT)])
                b=""


    def get_header(self, packet):
        try:
            h=packet[:HEADER_LENGTH*8]
            header={"target":bin_to_str(h[:4*8]), "seq":list(bin_to_int(h[4*8:4*8+2*8], 16))[0], "checksum":list(bin_to_int(h[4*8+2*8:4*8+2*8+2*8], 16))[0], "flag":list(bin_to_int(h[4*8+2*8+2*8:4*8+2*8+2*8+1*8]))[0]}
        except Exception as e:
            print(e)
            return(False)# header corrupted
        #print("header: ", header, "\n\n")
        return(header)

    def get_payload(self, packet, header):
        if not header:
            print("header corrupted")
            return(False)# header corrupted
        p=packet[HEADER_LENGTH*8:]
        if not int(checksum(p))==int(header["checksum"]):
            print("payload corrupted")
            return(False) # payload corrupted
        else:
            if int(header["flag"])==1: #is text
                return(bin_to_str(p))
            elif int(header["flag"])==0:
                return(bin_to_bytes(p))
            else:
                print("error in get_payload")

    def sort(self, packets):
        return(sorted(packets))


    def watch_queue(self):
        seqs=[]
        tmp=[]
        max_p=self.repeat*2
        while True:
            p=self.q.get()
            if p != '':
                seq=self.get_header(p)["seq"]
                name=self.get_header(p)["target"]
                if seq and seq not in seqs:
                    if self.get_payload(p, self.get_header(p)) and str(self.name)==str(name):
                        self.packets.put(p)
                        seqs.append(seq)
                        if seq==4095:
                            seqs=[]


    def recv(self):
        while True:
            p=self.packets.get()
            yield (self.get_header(p), self.get_payload(p, self.get_header(p)).replace("\x00", ""))

    def cleanup(self):
        try:
            del self.worker1
            del self.worker2
        except:
            pass #workers have not been defined yet
        gpio.cleanup()

