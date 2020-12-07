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
        b'You must set an initial admin password.\r\r\nPassword:',              # 0
        b'Re-enter password:',                                                  # 1
        device['name'].encode('utf-8') + b'#',                                  # 2
        'vedge'.encode('utf-8') + b'#',                                         # 3
        br'[Ll]ogin:',                                                          # 4
        b'Login incorrect\r\n' + device['name'].encode('utf-8') + b' login:',   # 5
        b'System Initializing. Please wait to login...',                        # 6
        b'Account locked due to',                                               # 7
        b'System Ready',                                                        # 8
        b'Password:',                                                           # 9
        b'Select storage device to use:',                                       # 10
        b'Login incorrect\r\n' + 'vedge'.encode('utf-8') + b' login:',          # 11
        # r'Password',
        # r'^You must set an initial admin password.',
        # r'^Re-enter password:',
        # r'.*#'
    ]
    track_incorrect = 0
    while True:
        time.sleep(5)
        idx, obj, output = telnet_obj.expect(responses, 5)
        s = output.decode('utf-8')
        print(s)

        # Search for more complicated patterns that are not working right with telnet expect
        if re.search('You must set an initial admin password.\r\r\nPassword:', s) is not None:
            # If initial setup prompted, send new password.
            telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
        elif re.search('Login incorrect', s) is not None:
            track_incorrect += 1
            print('Incorrect Logins: ' + str(track_incorrect))

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
            return obj, output
        elif idx == 5 or idx == 11:
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
        # If system initializing message received, add 20 seconds to sleep timer.
        elif idx == 6:
            if DEBUG:
                print('vManage is still initializing.  Waiting 20 seconds before trying again.')
            telnet_obj.write(b'\n')
            time.sleep(30)
        # If we get back 'account locked' or a prompt to select storage (vmanage), exit this routine.
        elif idx == 7 or idx == 10:
            if DEBUG:
                print('Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + ".  Exiting out of login loop.")
            return obj, output
        elif idx == 8:
            if re.search('login:', s) is None:
                if DEBUG:
                    print("Found system ready prompt.  Returning and looping one last time")
                telnet_obj.write(b'\n')
        else:
            if DEBUG:
                print("Didn't find a login prompt.  Looping to try again.")
            telnet_obj.write(b'\n')

        if track_incorrect >= 2:
            if DEBUG:
                print('Login incorrect.  Updating password to ' + device['preferred_password'])
            # If login is incorrect, try the preferred_password key on next loop
            device['password'] = device['preferred_password']


def pre_config_vmanage(telnet_obj, received_obj, received_output):
    prompts = [
        b'Would you like to format vdb? (y/n):',                # 0
        b'Select storage device to use:',                       # 1
        b'System Ready',                                        # 2
        b'The system is going down for reboot NOW!',            # 3
        b'login:',                                              # 4
    ]
    # Track first run of loop to pass received_output into output
    first_run = True
    while True:
        idx, obj, output = telnet_obj.expect(prompts, 2)
        if output is b' ':
            if first_run:
                output = received_output
                obj = received_obj

        s = output.decode()
        if DEBUG:
            print('Looping through pre_config for vManage')
        if re.search('Would you like to format vdb?', s):
            if DEBUG:
                print('Pattern matched for selecting device: Selected vdb as storage device.')
            telnet_obj.write(b"y\n")
            # Reboot will take 30+ minutes to complete.  Set timer at 40 minutes and watch for 'System Ready' message
            time_remaining = 2400
            sleep_interval = 30
            while time_remaining > 0:
                print(
                    'Waiting for vManage to build the hard drive.  ' +
                    str(time_remaining/60) +
                    ' minutes remaining.'
                )
                print(
                    'Do not shut down the VM during this process.'
                )
                time.sleep(sleep_interval)
                telnet_obj.write(b"\n")
                time_remaining -= sleep_interval
                idx, obj, output = telnet_obj.expect(prompts, 2)
                if idx == 2:
                    # System ready message returned.  Reduce timer to 0
                    time_remaining = 0
                elif idx == 3:
                    print('vManage is rebooting now.')
            # Once timer hits 0, exit the function and return True
            print('HDD Build on vManage is complete.  Continuing with configuration.')
            return True
        elif re.search('Select storage device to use:', s):
            if DEBUG:
                print('Pattern matched for selecting device: Selected vdb as storage device.')
            telnet_obj.write(b"1\n")
            time.sleep(2)
        else:
            telnet_obj.write(b"\n")
            time.sleep(2)
        first_run = False


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
                    telnet_obj, telnet_output = login_telnet(tn, device)
                    if device['name'] == 'vmanage' and not device['is_configured']:
                        pre_config_vmanage(tn, telnet_obj, telnet_output)
                    write_config(tn, device, config_lines)
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





