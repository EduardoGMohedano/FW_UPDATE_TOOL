import asyncio
import sys
import os
import time
import hashlib
from bleak import BleakScanner, BleakClient

client_address = ""
UUID_FW_SIZE =      "0000ff01"
UUID_FW_VERSION =   "0000ff02"
UUID_FW_PRJ_NAME =  "0000ff03"
UUID_FW_DATA =      "0000ff04"
chunk_size = 0 #Unit in bytes
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
    chunk_size = int(my_client.mtu_size) - 3
    
    #Fill the dictionary for all services using starting str as key and the full UUID string as value
    characteristics_dict = {}
    for service in my_client.services:
        for char in service.characteristics:

            
            if str(char.uuid).startswith(UUID_FW_VERSION):
                characteristics_dict[UUID_FW_VERSION] = char.uuid
                
            if str(char.uuid).startswith(UUID_FW_PRJ_NAME):
                characteristics_dict[UUID_FW_PRJ_NAME] = char.uuid

            if str(char.uuid).startswith(UUID_FW_SIZE):
                characteristics_dict[UUID_FW_SIZE] = char.uuid

            if str(char.uuid).startswith(UUID_FW_DATA):
                characteristics_dict[UUID_FW_DATA] = char.uuid
            #     print("Sending FW data to ESP32 device MAX MTU WITHOUT RESPONSE " + str(char.max_write_without_response_size) ) 
    

    #Operate using action menu
    while True:
        print("\n******Menu******")
        print("1. Read current Firmware version ")
        print("2. Read current Project name ")
        print("3. Start Firmware Update process ")
        print("q. Quit ")

        try:
            choice = input("Enter your action: ")
            if choice == "q":
                print("Exiting FW OTA BLE tool")
                break
            elif choice == "1":
                #Read fw version
                version = await my_client.read_gatt_char(characteristics_dict[UUID_FW_VERSION], used_cached=False)
                print("Current running project version is " + version.decode('utf-8'))
            elif choice == "2":
                #Read project name
                prj_name = await my_client.read_gatt_char(characteristics_dict[UUID_FW_PRJ_NAME], used_cached=False)
                print("Current running project name is " + prj_name.decode('utf-8'))
            elif choice == "3":
                #Start OTA process
                print("Starting OTA Process")
                fw_binary_size = str(os.path.getsize(fw_file))
                print("The Firmware binary size is "+ fw_binary_size)
                await my_client.write_gatt_char(characteristics_dict[UUID_FW_SIZE], fw_binary_size.encode('utf-8'), response=False)

                with open(fw_file, 'rb') as file:
                    while True:
                        chunk = file.read(chunk_size)

                        if not chunk:
                            print("\nNo more content to read from file ")
                            break

                        await my_client.write_gatt_char(characteristics_dict[UUID_FW_DATA], chunk, response=False)
                        hasher.update(chunk)
                        print_progress_bar(packet*chunk_size, int(fw_binary_size))
                        packet+=1
                        time.sleep(0.095)
                #print("The SHA256 of " + fw_file + " is " + hasher.hexdigest())

            else:
                print("\bInvalid choice, please use a valid option")           

        except KeyboardInterrupt:
            print("\nProgram terminated by the user")
            break

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