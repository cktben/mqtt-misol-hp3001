import argparse
import hid
import json
import paho.mqtt.client as mqtt
import struct
import time

ID_VENDOR = 0x0483
ID_PRODUCT = 0x5750

class HP3001:
    EP_OUT = 0x01
    EP_IN = 0x82

    def __init__(self):
        self._usb_device = None
        self._id_vendor = ID_VENDOR
        self._id_product = ID_PRODUCT

    def connect_usb(self):
        self._usb_device = hid.Device(self._id_vendor, self._id_product)

    def poll_usb(self):
        # Request current temperature and humidity measurements.
        self._usb_device.write(bytes([0x7b, 0x03, 0x40, 0x7d]))

        # Up to 64 bytes can be read, but the extra data is garbage.
        data = self._usb_device.read(27, timeout=500)
        if not data:
            raise Exception('Timeout')

        # Verify fixed header and trailer.
        if len(data) != 27 or data[0x00] != 0x7b or data[0x19] != 0x40 or data[0x1a] != 0x7d:
            raise Exception('Invalid measurements')

        values = struct.unpack('>hBhBhBhBhBhBhBhB', data[0x01:0x19])
        temperature = [x / 10 for x in values[::2]]
        humidity = values[1::2]

        return temperature, humidity

class HP3001toMQTT:
    def __init__(self):
        self._mqtt = None
        self._device = None
        self._mqtt_config = {}
        self._config = {}

    def connect_mqtt(self, config_filename):
        with open(config_filename, 'r') as f:
            self._mqtt_config = json.load(f)

        self._mqtt = mqtt.Client()
        username = self._mqtt_config.get('username')
        if username:
            self._mqtt.username_pw_set(username, self._mqtt_config.get('password'))
        if self._mqtt_config.get('use_tls', False):
            self._mqtt.tls_set(self._mqtt_config.get('ca_certs'), self._mqtt_config.get('certfile'), self._mqtt_config.get('keyfile'))
        self._mqtt.connect(self._mqtt_config.get('host', 'localhost'), self._mqtt_config.get('port', 1883))

        self._mqtt.loop_start()

    def load_config(self, config_filename):
        with open(config_filename, 'r') as f:
            self._config = json.load(f)

        if type(self._config) != dict:
            raise Exception('Configuration must be an object')

    def connect_device(self):
        self._device = HP3001()
        self._device.connect_usb()

    def run(self):
        period = float(self._config.get('period', '30'))
        topic_root = self._config.get('mqtt_topic_root', '')
        if topic_root and not topic_root.endswith('/'):
            topic_root += '/'

        while True:
            start_time = time.time()

            temperature, humidity = self._device.poll_usb()
            for ch in range(8):
                ch_label = str(ch + 1)
                topic_base = topic_root + ch_label
                topic_temperature = topic_base + '/temperature'
                topic_humidity = topic_base + '/humidity'
                self._mqtt.publish(topic_temperature, str(temperature[ch]))
                self._mqtt.publish(topic_humidity, str(humidity[ch]))

            end_time = time.time()
            delay = max(0, period - (end_time - start_time))
            time.sleep(delay)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Configuration file', default='hp3001.json')
    parser.add_argument('-m', '--mqtt-config', help='MQTT configuration file', default='mqtt.json')
    args = parser.parse_args()

    service = HP3001toMQTT()
    service.load_config(args.config)
    service.connect_mqtt(args.mqtt_config)
    service.connect_device()
    service.run()
