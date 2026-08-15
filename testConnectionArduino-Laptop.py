import serial, time
s=serial.Serial('COM3',9600,timeout=1)
time.sleep(2)
s.write(b'FAIL\\n')
print('wrote FAIL')
time.sleep(2)
s.close()