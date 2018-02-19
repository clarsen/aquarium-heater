import os
import glob
import time
import RPi.GPIO as GPIO
import requests

HEALTHCHECK_URL='https://hchk.io/<YOUR_ID_HERE>'
INFLUX_HOST='<YOUR_HOST_HERE>'
INFLUX_DB='<YOUR_DB_HERE>'

# This has already been done by /boot/config.txt:
# os.system('modprobe w1-gpio')
# os.system('modprobe w1-therm')

from influxdb import InfluxDBClient
client = InfluxDBClient(host=INFLUX_HOST, port=8086, database=INFLUX_DB, timeout=10)

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.OUT, initial=0)

set_temp = 79.0 # betta fish like 78-80 F


try:
    while True:
        temp_c, temp_f = read_temp()
        print(temp_c, temp_f)

        # just a bit of leeway to avoid cycling too often.
        if temp_f < (set_temp-0.5):
            print("heat on")
            heat = 1
        elif temp_f > (set_temp+0.5):
            print("heat off")
            heat = 0
        GPIO.output(21, heat)
        json_body = []
        json_body.append({
            "measurement": "saltine.temp_f",
            "tags": {
            },
            "fields": {
                "value": float(temp_f),
            }
        })
        client.write_points(json_body)
        requests.get(HEALTHCHECK_URL, timeout=10)


        time.sleep(10)
except KeyboardInterrupt:
    GPIO.cleanup()
