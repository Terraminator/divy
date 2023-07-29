from transceiver import *
transmitter=tx(17, "pi4b", repeat=1)
#while True:

#gpio.output(17, 1)
#sleep(5)
#gpio.output(17, 0)
for i in range(1):
	try:
		print("sending...")
		transmitter.send("hallo")
	except Exception as e:
		print(e)
		transmitter.cleanup()
		exit(0)
transmitter.cleanup()
exit(0)

