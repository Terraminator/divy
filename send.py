from transceiver import *
transmitter=tx(17, "pi4b", repeat=10)

for i in range(20):
	try:
		print("sending hallo...")
		transmitter.send("hallo")
	except Exception as e:
		print(e)
		transmitter.cleanup()
		exit(0)
transmitter.cleanup()
exit(0)

