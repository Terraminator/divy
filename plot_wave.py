import RPi.GPIO as GPIO
import matplotlib.pyplot as plt
import random
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN)

data=""
t1=time.time_ns()
lsig=None
lt=0
et=(10**9)*20#20s
while time.time_ns()-t1<et:
    sig=GPIO.input(27)
    if lsig!=sig:
        delta_t=time.time_ns()-lt
        lt=time.time_ns()
        lsig=sig
        data+=str(lt-t1) + ":" + str(delta_t) + ":" + str(sig) + "\n"
    
GPIO.cleanup()

data=data[:len(data)-1]
print("evaluating data...")
timestamps=[]
signal_values=[]
delta_ts=[]
start=int(data.split("\n")[0].split(":")[0])
for x in data.split("\n"):
    t=int(x.split(":")[0])
    td=int(x.split(":")[1])
    y=int(x.split(":")[2])
    timestamps.append(int(t)-start)
    delta_ts.append(int(td))
    signal_values.append(int(y))

print(list(zip(timestamps, signal_values, delta_ts)))
print("plotting data...")

scope=5
plt.step(timestamps[:scope], signal_values[:scope], 'r')

plt.show()
