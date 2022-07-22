# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
# See https://docs.pycom.io for more information regarding library specif


import machine
import struct
import time
import pycom
import socket
import ubinascii
import cayenneLPP
from pycoproc_1 import Pycoproc
from LIS2HH12 import LIS2HH12
from LTR329ALS01 import LTR329ALS01
from network import LoRa
from network import WLAN
from machine import RTC


# Make sure heartbeat is disabled before setting RGB LED
pycom.heartbeat(False)
pycom.rgbled(0x0000FF) # Blue

# Connect to wifi to get time
wlan = WLAN(mode=WLAN.STA)
wlan.connect(ssid='YOUR SSID', auth=(WLAN.WPA2, 'YOUR PASSWORD'))
while not wlan.isconnected():
    machine.idle()
time.sleep(1)
print('\n')
print("WiFi connected succesfully to :")
print(wlan.ifconfig()) # Print IP configuration
pycom.rgbled(0x0000FF) # Blue
time.sleep(5)


# setup rtc
rtc = machine.RTC()
rtc.ntp_sync("pool.ntp.org")
time.sleep(0.75)
print('\nRTC Set from NTP to UTC:', rtc.now())
time.timezone(-14200)
print('Adjusted from UTC to EST timezone', time.localtime(), '\n')
print("Local time: ", time.localtime())
a = rtc.synced()
print('RTC is synced to "pool.ntp.org": ', a)


pyscan = Pycoproc(Pycoproc.PYSCAN)
py = Pycoproc(Pycoproc.PYSCAN)

ltr329als01 = LTR329ALS01() # Digital Ambient Light Sensor
lis2hh12 = LIS2HH12() # 3-Axis Accelerometer

# Initialise LoRa in LORAWAN mode.
# Please pick the region that matches where you are using the device:
# Asia = LoRa.AS923
# Australia = LoRa.AU915
# Europe = LoRa.EU868
# United States = LoRa.US915
lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.US915)

# create an OTAA authentication parameters, change them to the provided credentials
app_eui = ubinascii.unhexlify('YOUR app_eui')
app_key = ubinascii.unhexlify('YOUR app_key')
#uncomment to use LoRaWAN application provided dev_eui
dev_eui = ubinascii.unhexlify('YOUR dev_eui')


# Get device info
dev_eui = ubinascii.unhexlify('YOUR dev_eui')
print('\n') 
print("** DevEUI: %s" % (ubinascii.hexlify(lora.mac())))
print('\n') 

# Uncomment for US915 / AU915 & Pygate
for i in range(0,8):
    lora.remove_channel(i)
for i in range(16,65):
    lora.remove_channel(i)
for i in range(66,72):
    lora.remove_channel(i)

# join a network using OTAA (Over the Air Activation)
#uncomment below to use LoRaWAN application provided dev_eui
lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
#lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    pycom.rgbled(0x7f0d00) # Red
    time.sleep(1.0)
    pycom.rgbled(0x000000) # Black(off)
    time.sleep(1.0)
    print('Not yet joined...')

print('\n')
print('LORA OTTA Joined')
print('\n')
pycom.rgbled(0x001400) # Green

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 2)

while True:
    # make the socket blocking
    # (waits for the data to be sent and for the 2 receive windows to expire)
    s.setblocking(True)
    lpp = cayenneLPP.CayenneLPP(size = 100, sock = s)
    # Read the values from the sensors
    acceleration = lis2hh12.acceleration()
    acceleration_x = lis2hh12.acceleration_x() 
    acceleration_y = lis2hh12.acceleration_y()
    acceleration_z = lis2hh12.acceleration_z()
    voltage = pyscan.read_battery_voltage()
    light = ltr329als01.light()[0]
    lux = ltr329als01.lux()
    roll = lis2hh12.roll()
    pitch = lis2hh12.pitch()
    # Debug sensor values
    print('voltage: {}, lumen: {}, lux: {}, roll: {}, pitch: {}, acceleration: {}'.format(voltage, light, lux, roll, pitch, acceleration))
    print('\nacceleration x: {}, acceleration y: {}, acceleration z: {}'.format(acceleration_x, acceleration_y, acceleration_z))
    print('\n')
    # # Convert to byte array for transmission
    lpp.add_accelerometer(acceleration_x, acceleration_y, acceleration_z, channel = 9)
    lpp.add_luminosity(light, channel = 5)
    lpp.add_luminosity(lux, channel = 6)
    lpp.send(reset_payload = True)

    print("Bytes sent to TTN, sleeping for 5 secs")
    print("\nLocal time: ", time.localtime())
    print("\nIP configuration: ", wlan.ifconfig()) # Print IP configuration
    pycom.rgbled(0xFFFF00) # Yellow
    time.sleep(5)
    # make the socket non-blocking
    # (because if there's no data received it will block forever...)
    s.setblocking(False)
    # get any data received (if any...)
    data = s.recv(64)
    print('\n')
    print("Data received: ", data)
    pycom.rgbled(0xFFFFFF) # White
    print('\n')
