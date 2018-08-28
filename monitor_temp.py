import glob
import time
import RPi.GPIO as GPIO
import requests
from influxdb import InfluxDBClient
import yaml
import PID

config = yaml.load(open("config.yaml"))

client = InfluxDBClient(
    host=config['influx_host'],
    port=8086,
    timeout=10,
    database=config['influx_db'],
    ssl=True,
    verify_ssl=config['influx_host_verify_cert'],
    username=config['influx_user'],
    password=config['influx_password'],
)

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
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f


def pwm_heater_control_loop(state):
    """PID controlled loop using PWM to control heat output"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(21, GPIO.OUT, initial=0)
    GPIO.output(21, 0)
    time.sleep(20)  # wait for other PID process to determine output
    period = config['heatperiod']

    while True:
        if state['pid'] > 1:  # 100%
            print("on")
            GPIO.output(21, 1)
            time.sleep(30)
        elif state['pid'] <= 0:  # 0%
            print("off")
            GPIO.output(21, 0)
            time.sleep(30)
        else:
            on_sec = state['pid'] * period
            if on_sec >= period:
                on_sec = period
            if on_sec < 0:
                on_sec = 0

            print("on for {:3.2f}%% ({:3.2f} sec)".format(
                on_sec / period * 100.0, on_sec))
            GPIO.output(21, 1)
            time.sleep(on_sec)

            print("off for {:3.2f}%% ({:3.2f} sec)".format(
                (period - on_sec) / period * 100.0, period - on_sec))
            GPIO.output(21, 0)
            time.sleep(period - on_sec)


def pid_control(state):
    pid = PID.PID(config['pid_P'], config['pid_I'], config['pid_D'])
    pid.SetPoint = state['set_temp']
    pid.setSampleTime(config['pid_sample_period'])
    pid.setWindup(config['pid_windup'])

    while True:
        temp_c, temp_f = read_temp()
        print(temp_c, temp_f)
        state['temp_f'] = temp_f
        start = time.clock()
        next = start + config['pid_sample_period']

        pid.update(state['temp_f'])
        print("pid.output={}".format(pid.output))
        print("P,I,D={}".format(pid.pidterms()))
        state['pid'] = pid.output

        json_body = []
        json_body.append({
            "measurement": "saltine.temp_f",
            "tags": {
            },
            "fields": {
                "value": float(temp_f),
            }
        })

        try:
            # sometimes network requests fail, but don't fail this loop
            client.write_points(json_body)
            requests.get(config['healthcheck_url'], timeout=10)
        except Exception as e:
            print(e)
            pass

        until_next_period = next - time.clock()
        if until_next_period > 0:
            time.sleep(until_next_period)


if __name__ == '__main__':
    from threading import Thread
    temp_c, temp_f = read_temp()


    state = {}
    state['on_temp'] = config['set_temp'] + config['on_temp_offset']
    state['off_temp'] = config['set_temp'] + config['off_temp_offset']
    state['temp_f'] = temp_f
    state['set_temp'] = config['set_temp']
    state['pid'] = 0

    try:
        h = Thread(target=pwm_heater_control_loop, args=(state,))
        h.daemon = True
        h.start()

        p = Thread(target=pid_control, args=(state,))
        p.daemon = True
        p.start()

        while h.is_alive() and p.is_alive():

            time.sleep(5)
    except KeyboardInterrupt:
        GPIO.cleanup()
