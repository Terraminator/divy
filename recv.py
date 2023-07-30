from transceiver import *
receiver=rx(27, "pi4b", repeat=10)
while True:
	try:
		for x in receiver.recv():
			print("recv.py: ", x)
	except Exception as e:
		print(e)
		receiver.cleanup()
		exit(0)
