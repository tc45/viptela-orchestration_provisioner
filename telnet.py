from pythonping import ping
import telnetlib
import time
from tabulate import tabulate
import re

HOST = '172.28.43.171'
user = 'admin'
password = 'insight'

LOGGED_IN = False
ALL_COMPLETE = False
DEBUG = True

# Create vManage, vBond, and vSmart objects.  Associate default configuration files with each object.  Add to list.

vSmart = {
    'name': 'vsmart',
    'port': '32771',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.3',
    'is_configured': False,
    'initial_config_file': 'configs/vsmart-initial.txt',
}
vBond = {
    'name': 'vbond',
    'port': '32770',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.2',
    'is_configured': False,
    'initial_config_file': 'configs/vbond-initial.txt',
}
vManage = {
    'name': 'vmanage',
    'port': '32769',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.1',
    'is_configured': False,
    'initial_config_file': 'configs/vmanage-initial.txt',
}

v_devices = [vManage, vSmart, vBond]


device_details = []


def login_telnet(telnet_obj, device):
    responses = [
        b'You must set an initial admin password.\r\r\nPassword:',
        b'Re-enter password:',
        device['name'].encode('utf-8') + b'#',
        'vedge'.encode('utf-8') + b'#',
        br'[Ll]ogin:',
        b'Login incorrect',
        b'System Initializing. Please wait to login...',
        b'Account locked due to',
        b'System Ready',
        b'Password:',
        b'Select storage device to use:',
        # r'Password',
        # r'^You must set an initial admin password.',
        # r'^Re-enter password:',
        # r'.*#'
    ]
    track_incorrect = 0
    while True:
        time.sleep(5)
        idx, obj, output = telnet_obj.expect(responses, 2)
        # If login prompt found, send username
        if idx == 0:
            telnet_obj.write(device['preferred_password'].encode('ascii') + b"\n")
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + '.  Setting initial password.  Sending password ' + device['preferred_password'])
        elif idx == 4:
            telnet_obj.write(device['username'].encode('ascii') + b"\n")
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + '.  Found login prompt.  Sending username ' + device['username'])
        # If Password prompt found, send password
        elif idx == 9:
            if output.decode('utf-8').find('You must set an initial admin password.') >= 0:
                # If initial setup prompted, send new password.
                telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
                time.sleep(5)
            else:
                if DEBUG:
                    print('Found password prompt.  Sending password ' + device['password'])
                # If initial setup not prompted, send regular password.
                telnet_obj.write(device['password'].encode('ascii') + b"\n")
                time.sleep(5)
                idx, obj, output = telnet_obj.expect(responses, 10)
                if idx == 0:
                    telnet_obj.write(device['preferred_password'].encode('ascii') + b"\n")
                    if DEBUG:
                        print('Pattern matched: ' + obj.re.pattern.decode(
                            'utf-8') + '.  Setting initial password.  Sending password ' + device['preferred_password'])
                elif idx == 5:
                    track_incorrect += 1
                    print('Incorrect Logins: ' + str(track_incorrect))
                    if track_incorrect >= 2:
                        if DEBUG:
                            print('Login incorrect.  Updating password to ' + device['preferred_password'])
                        # If login is incorrect, try the preferred_password key on next loop
                        device['password'] = device['preferred_password']
                elif idx == 6:
                    # If System is still initializing, wait 30 seconds before trying again..
                    if DEBUG:
                        print('vManage is still initializing.  Waiting 20 seconds before trying again.')
                    time.sleep(20)
                    telnet_obj.write(b'\n')
                elif idx == 9:
                    telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
                    time.sleep(5)
                elif idx == 10:
                    if DEBUG:
                        print('Pattern matched: ' + obj.re.pattern.decode(
                            'utf-8') + ".  Exiting out of login loop.")
                    break
        elif idx == 1:
            telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
            device['password'] = device['preferred_password']
            if DEBUG:
                print('Found re-enter password prompt.  Sending password ' + device['preferred_password'])
        elif idx == 2 or idx == 3:
            prompt_result = idx
            if DEBUG:
                print('Device prompt ' + obj.re.pattern.decode('utf-8') + " was found.  Setting password to preferred and exiting login function.")
            device['password'] = device['preferred_password']
            break
        elif idx == 5:
            if output.decode('utf-8').find('System Initializing. Please wait to login...') >= 0:
                if DEBUG:
                    print('vManage is still initializing.  Waiting 20 seconds before trying again.')
                time.sleep(20)
            else:
                track_incorrect += 1
                print('Incorrect Logins: ' + str(track_incorrect))
                if track_incorrect >= 2:
                    if DEBUG:
                        print('Incorrect login detected.  Updating to preferred password and looping.')
                    # If login is incorrect, try the preferred_password key on next loop
                    device['password'] = device['preferred_password']
        elif idx == 6:
            if DEBUG:
                print('vManage is still initializing.  Waiting 20 seconds before trying again.')
            telnet_obj.write(b'\n')
            time.sleep(30)
        # If we get back either a hostname prompt (#) or a prompt to select storage (vmanage), exit this routine.
        elif idx == 7 or idx == 10:
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + ".  Exiting out of login loop.")
            break
        elif idx == 8:
            if DEBUG:
                print("Found system ready prompt.  Returning and looping one last time")
            telnet_obj.write(b'\n')
        else:
            if DEBUG:
                print("Didn't find a login prompt.  Looping to try again.")
            telnet_obj.write(b'\n')


def pre_config_vmanage(telnet_obj):
    prompts = [
        b'Would you like to format vdb? (y/n):',
        b'Select storage device to use:',
        b'System Ready',
    ]
    while True:
        idx, obj, output = telnet_obj.expect(prompts, 2)
        if DEBUG:
            print('Looping through pre_config for vManage')
        if idx == 0:
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + ".  Formatting vdb.")
            telnet_obj.write(b"y\n")
            time_remaining = 2400
            sleep_interval = 30
            while time_remaining > 0:
                print('Waiting for vManage to build the hard drive.  ' + str(time_remaining/60) + ' minutes remaining.' )
                time.sleep(sleep_interval)
                time_remaining -= sleep_interval
                idx, obj, output = telnet_obj.expect(prompts, 2)
                if idx == 3:
                    time_remaining = 0
            break
        if idx == 2:
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + ".  Selected vdb as storage device.")
            telnet_obj.write(b"1\n")
            time.sleep(2)
        else:
            telnet_obj.write(b"\n")
            time.sleep(2)


def write_config(telnet_obj, device, config):
    prompts = [
        device['name'].encode('utf-8') + b'#',
        'vedge'.encode('utf-8') + b'#',

    ]

    is_config_applied = device['is_configured']

    while not is_config_applied:
        idx, obj, output = telnet_obj.expect(prompts, 2)
        if idx == 0 or idx == 1:
            pass                                 # TODO: Finish this part up.

    telnet_obj.write(b'\n')
    time.sleep(2)
    print('Logged in.  Beginning to send commands.')
    telnet_obj.write(b'\n')
    time.sleep(2)

    for line in config:
        telnet_obj.write(line.encode())

    time.sleep(5)
    telnet_obj.write(b'exit\n')
    # telnet_obj.write(b'show int | tab\n')

    print('Closing telnet object')

    telnet_obj.close()
    print(telnet_obj.read_all().decode('ascii'))


for device in v_devices:
    details = [device['name'], HOST, device['port']]
    device_details.append(details)

print('\nThe following default values will be used to initial provision the Viptela POD.\n')
print(tabulate(device_details, headers=['DEVICE', 'HOST', 'PORT'], tablefmt="pretty"))
# response = input('Would you like to make changes to these values [y/n]') or 'n'

while not ALL_COMPLETE:
    for device in v_devices:
        # If device key for configuration is set to False:
        # Ping the device VPN0 ip.  If it responds, mark as configured.
        # If it does not respond, continue with configuration.
        if not device['is_configured']:
            response = ping(device['vpn0_ip'], count=1)
            if response.packets_lost == 0:
                print(device['name'] + ' is active!')
                device['is_configured'] = True
            else:
                print(device['name'] + ' is NOT active.  Attempting to configure.')
                # print(response)
                config = open(device['initial_config_file'], 'r')
                config_lines = config.readlines()
                try:
                    tn = telnetlib.Telnet(HOST, device['port'])
                    # tn.write(b'exit\n')
                    login_telnet(tn, device)
                    if device['name'] == 'vmanage' and not device['is_configured']:
                        pre_config_vmanage(tn)
                    # write_config(tn, device, config_lines)
                    # print(tn.read_all())
                except ConnectionRefusedError as error:
                    print('Connection was refused to ' + HOST + ' on port ' + device['port'] + '.')

    time.sleep(5)
    track_configured = 0
    for device in v_devices:
        if device['is_configured']:
            track_configured += 1

    print(60 * '*')
    print(str(track_configured) + ' out of ' + str(len(v_devices)) + ' Viptela device configurations completed.')
    print(60 * '*')
    print('\n')

    if track_configured == len(v_devices):

        ALL_COMPLETE = True





