import serial
import time

arduino = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

arduino.write(b'FAIL\n')

arduino.write(b'PASS\n')