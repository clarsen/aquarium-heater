import os
import glob
import time
import RPi.GPIO as GPIO
import requests

import yaml
config = yaml.load(open("config.yaml"))

from influxdb import InfluxDBClient
client = InfluxDBClient(host=config['influx_host'],
                        port=8086,
                        database=config['influx_db'],
                        timeout=10)

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

off_temp = config['set_temp'] + config['off_temp_offset']
on_temp = config['set_temp'] + config['on_temp_offset']


try:
    while True:
        temp_c, temp_f = read_temp()
        print(temp_c, temp_f)

        # just a bit of leeway to avoid cycling too often.
        if temp_f <= on_temp:
            print("heat on")
            heat = 1
        elif temp_f >= off_temp:
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
        requests.get(config['healthcheck_url'], timeout=10)

        time.sleep(10)
except KeyboardInterrupt:
    GPIO.cleanup()
