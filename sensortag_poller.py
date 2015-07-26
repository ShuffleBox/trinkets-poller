import logging
import time
import requests
from requests.auth import HTTPBasicAuth
from gattlib import DiscoveryService
from libcc2650 import SensorTag
import ipdb

#BTLE device scan 
BT_ADAPTER = "hci0"
SCAN_TTL = 2  #how long to search during BTLE discovery
LOOP_WAIT = 2 #Delay scanning tags for 15 seconds

#WebHost for value logging
WEBHOST = 'localhost:8000'
API_PATH = '/api/v1/sensortags/'
USERNAME = 'update_user'
PASSWORD = 'user_pwrd'

def SensorTagDeviceScan(bt_adapter, scan_ttl):
    """
    Discovers BTLE devices that describe themselves
    as a SensorTag.
    """
    service = DiscoveryService(bt_adapter) 
    devices = service.discover(scan_ttl)
    for key in devices.keys():
        if 'SensorTag' not in devices[key]:
            del devices[key]
    
    return devices
        
def HTTPUpdateTag(tag, payload):
    """
    build and send web request from Sensortag values
    TO THINK on: two ambient temp values to choose from
    due to humidity and ir_temp sensors - currently using humidity sensor
    """

    TAG_STUB = payload['mac_address'].replace(":", "")
    POST_URL = "http://" + WEBHOST + API_PATH + TAG_STUB + "/"
    #ipdb.set_trace()
    r = requests.post(POST_URL, auth=HTTPBasicAuth(USERNAME, PASSWORD), data=payload, timeout=2)
    return None

if __name__ == "__main__":
    """
    1. Get SensortTag BTLE MACs
    2. Interrogate SensorTags
    3. POST results to website
    4. Wait LOOP_WAIT seconds and do it again
    """
    while True:
        devices = SensorTagDeviceScan(BT_ADAPTER, SCAN_TTL)
        print devices
        print "\n" + str(len(devices)) + " devices found \n"
        count = 0
        for device in devices:
            """ 
              originally would attach to the tag, wake up the sensors
              then read in all the values to a dictionary in one step.
              refactoring to read in values one at a time and turn
              sensors on and off as needed.
            """
            
            try:
                payload = {}
                tag = SensorTag(device)
                time.sleep(3)
                payload['mac_address'] = tag.deviceAddr
                tag.IRtemperature.enable()
                time.sleep(2)
                payload['ir_temp'] = tag.IRtemperature.read()[1]
                tag.IRtemperature.disable()
                time.sleep(.5)
                tag.humidity.enable()
                time.sleep(1)
                payload['ambient_temp'] = tag.humidity.read()[0]
                time.sleep(.5)
                payload['humidity'] = tag.humidity.read()[1]
                tag.humidity.disable()
                time.sleep(.5)
                tag.luxometer.enable()
                time.sleep(1)
                payload['lux'] = tag.luxometer.read()
                time.sleep(.5)
                tag.luxometer.disable()
                time.sleep(.5)
                tag.waitForNotifications(5)
                tag.disconnect()
                
                print "device " + str(count) + " = " 
                print payload
                HTTPUpdateTag(tag, payload)

            except Exception:
                logging.exception("baah")
                tag.disconnect() #if there is a problem try to disconnect
                break

                """ 
                The tags will wait forever (effectively lockup) if the session does not disconnect.
                This could be signal drop off, a thrown exception that doesnt clean up after, or
                if they just get moody.. lets do our best to disconnect cleanly.
                """

            count += 1

        time.sleep(LOOP_WAIT)
