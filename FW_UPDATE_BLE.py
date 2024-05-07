import asyncio
import sys
import os
import time
import hashlib
from bleak import BleakScanner, BleakClient

client_address = ""
UUID_FW_DATA = "0000ff03"
UUID_FW_SIZE = "0000ff01"
chunk_size = 350 #Unit in bytes
connection_timeout = 15 #Used in seconds
hasher = hashlib.sha256()

#Print the current progress of FW update using a bar
def print_progress_bar(progress, total, bar_length=50):
    percent = int((progress / total) * 100)
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f'\r|{bar}| {percent}% Complete')
    sys.stdout.flush()

async def main(fw_file):
    devices = await BleakScanner.discover()
    index_device = 0
    devices_dict = {}
    print("The discovered devices are: ")
    for d in devices:
        print("["+ str(index_device) +"]"+ " " + d.address + " " + str(d.name))
        devices_dict[index_device] = d.address
        index_device = index_device+1
    
    #Choose a device using index number
    device_no = int(input("Choose a device number to connect: "))
    if( device_no >= index_device):
        print("Error: That's not a valid device integer number!", file=sys.stderr)
        sys.exit(1)
    
    #Start the connection
    packet = 1
    client_address = devices_dict[device_no]
    my_client = BleakClient(client_address)

    await my_client.connect(timeout=connection_timeout)
    print("We are connected to device address: " + client_address + " with a negotiated MTU size of " + str(my_client.mtu_size) + " bytes")
    for service in my_client.services:
        for char in service.characteristics:
            
            if str(char.uuid).startswith(UUID_FW_SIZE):
                fw_binary_size = str(os.path.getsize(fw_file))
                print("The Firmware binary size is "+ fw_binary_size + " and its sent to UUID " + str(char.uuid))
                await my_client.write_gatt_char(char.uuid, fw_binary_size.encode('utf-8'), response=False)

            if str(char.uuid).startswith(UUID_FW_DATA):
                print("Sending FW data to ESP32 device")
                with open(fw_file, 'rb') as file:
                    while True:
                        chunk = file.read(chunk_size)

                        if not chunk:
                            print("\nNo more content to read from file ")
                            break

                        await my_client.write_gatt_char(char.uuid, chunk, response=False)
                        hasher.update(chunk)
                        print_progress_bar(packet*chunk_size, int(fw_binary_size))
                        packet+=1
                        time.sleep(0.095)
                print("The SHA256 of " + fw_file + " is " + hasher.hexdigest())
    
    await my_client.disconnect()

if __name__ == "__main__":
    if( len(sys.argv) > 1 ):
        input_string = sys.argv[1]
        if os.path.exists(input_string):
            asyncio.run(main(input_string))
        else:
            print("Error the FW binary file does not exist")
    else:
        print("Please provide a FW binary name as argument")