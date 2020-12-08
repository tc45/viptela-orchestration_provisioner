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


def login2(telnet_obj, device):
    prompts = [
        br'[lL]ogin:',                              # 0
        device['name'].encode('utf-8') + b'#',      # 1
        'vedge'.encode('utf-8') + b'#',             # 2
        b'Password:',                               # 3
        b'Welcome to Viptela CLI',                  # 4
        b'Select storage device to use:',           # 5
    ]

    track_incorrect = 0

    while True:
        time.sleep(5)
        idx, obj, output = telnet_obj.expect(prompts, 5)
        s = output.decode()

        # Search for more complicated patterns that are not working right with telnet expect
        # if re.search('You must set an initial admin password.\r\r\nPassword:', s) is not None:
        #     # If initial setup prompted, send new password.
        #     telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
        if re.search('System Initializing. Please wait to login...', s) is not None:
            print("In this function now.")
            #telnet_obj.write(b'\n')
            if DEBUG:
                print('vManage is still initializing.  Waiting up to 180 seconds for system to be ready before trying again.')
            return_val = telnet_obj.read_until(b'System Ready', timeout=180)
            if return_val is not b' ':
                time.sleep(3)
                print('vManage is Ready. Logging in now.')
                telnet_obj.write(b'\n')
                telnet_obj.write(device['username'].encode('ascii') + b"\n")
                time.sleep(5)
                telnet_obj.write(device['password'].encode('ascii') + b"\n")
        elif re.search('Login incorrect', s) is not None:
            track_incorrect += 1
            print('Incorrect Logins: ' + str(track_incorrect))
        elif re.search('You must set an initial admin password', s) is not None:
            if DEBUG:
                print('Setting initial admin passwords')
            # If initial setup prompted, send new password.
            match_passwords(telnet_obj, device['preferred_password'])
            return True
        # If login prompt found, send username followed by password
        elif idx == 0:
            if DEBUG:
                print('- Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + '.  Found login prompt.  Sending username ' + device['username'])
            telnet_obj.write(device['username'].encode('ascii') + b"\n")
        elif idx == 3:
            if DEBUG:
                print('- Pattern matched: ' + obj.re.pattern.decode(
                    'utf-8') + '  Setting password.  Sending password ' + device['password'])
            telnet_obj.write(device['password'].encode('ascii') + b"\n")
        elif idx == 1 or idx == 2:
            return
        elif idx == 4 or idx == 5:
            return
        else:
            telnet_obj.write(b'\n')
            if DEBUG:
                print('Login prompt not found.  Looping function.')

        if track_incorrect >= 2:
            device['password'] = device['preferred_password']
            if DEBUG:
                print('Incorrect password 2 times.  Updating password to preferred password: ' +
                      device['preferred_password'])


def match_passwords(telnet_obj, new_password):
    passwords_match = False

    while not passwords_match:
        telnet_obj.write(new_password.encode('ascii') + b'\n')
        telnet_obj.read_until(b'Re-enter password:', 20)
        telnet_obj.write(new_password.encode('ascii') + b'\n')

        prompts = [
            b'Try again...',
            b'#',
        ]

        idx, obj, output = telnet_obj.expect(prompts, 15)

        if idx == 0:
            if DEBUG:
                print("Passwords don't match. Try again.")
        elif idx == 1:
            if DEBUG:
                print("Passwords matched and were accepted.  Continuing")
            passwords_match = True
            return True



# def login_telnet(telnet_obj, device):
#     responses = [
#         b'You must set an initial admin password.\r\r\nPassword:',              # 0
#         b'Re-enter password:',                                                  # 1
#         device['name'].encode('utf-8') + b'#',                                  # 2
#         'vedge'.encode('utf-8') + b'#',                                         # 3
#         br'[Ll]ogin:',                                                          # 4
#         b'Login incorrect\r\n' + device['name'].encode('utf-8') + b' login:',   # 5
#         b'System Initializing. Please wait to login...',                        # 6
#         b'Account locked due to',                                               # 7
#         b'System Ready',                                                        # 8
#         b'Password:',                                                           # 9
#         b'Select storage device to use:',                                       # 10
#         b'Login incorrect\r\n' + 'vedge'.encode('utf-8') + b' login:',          # 11
#         # r'Password',
#         # r'^You must set an initial admin password.',
#         # r'^Re-enter password:',
#         # r'.*#'
#     ]
#     track_incorrect = 0
#     while True:
#         time.sleep(5)
#         idx, obj, output = telnet_obj.expect(responses, 5)
#         s = output.decode('utf-8')
#         print(s)
#
#         # Search for more complicated patterns that are not working right with telnet expect
#         if re.search('You must set an initial admin password.\r\r\nPassword:', s) is not None:
#             # If initial setup prompted, send new password.
#             match_passwords(device['preferred_password'])
#         elif re.search('System Initializing. Please wait to login...', s) is not None:
#             if DEBUG:
#                 print('vManage is still initializing.  Waiting up to 180 seconds for system to be ready before trying again.')
#             return_val = telnet_obj.read_until(b'System Ready', timeout=180)
#
#             if return_val is not b' ':
#                 print('vManage is Ready. Logging in now.')
#                 telnet_obj.write(b'\n')
#         elif re.search('System Ready', s) is not None:
#             if DEBUG:
#                 print('vManage is ready to be logged in.')
#             telnet_obj.write(b'\n')
#         elif re.search('Login incorrect', s) is not None:
#             track_incorrect += 1
#             print('Incorrect Logins: ' + str(track_incorrect))
#
#         # If login prompt found, send username
#         elif idx == 0:
#             telnet_obj.write(device['preferred_password'].encode('ascii') + b"\n")
#             if DEBUG:
#                 print('Pattern matched: ' + obj.re.pattern.decode(
#                     'utf-8') + '  Setting initial password.  Sending password ' + device['preferred_password'])
#         elif idx == 4:
#             telnet_obj.write(device['username'].encode('ascii') + b"\n")
#             if DEBUG:
#                 print('Pattern matched: ' + obj.re.pattern.decode(
#                     'utf-8') + '.  Found login prompt.  Sending username ' + device['username'])
#         # If Password prompt found, send password
#         elif idx == 9:
#             if output.decode('utf-8').find('You must set an initial admin password.') >= 0:
#                 # If initial setup prompted, send new password.
#                 match_passwords(device['preferred_password'])
#             else:
#                 if DEBUG:
#                     print('Found password prompt.  Sending password ' + device['password'])
#                 # If initial setup not prompted, send regular password.
#                 telnet_obj.write(device['password'].encode('ascii') + b"\n")
#                 time.sleep(5)
#         elif idx == 1:
#             telnet_obj.write(device['preferred_password'].encode('ascii') + b'\n')
#             device['password'] = device['preferred_password']
#             if DEBUG:
#                 print('Found re-enter password prompt.  Sending password ' + device['preferred_password'])
#         elif idx == 2 or idx == 3:
#             prompt_result = idx
#             if DEBUG:
#                 print('Device prompt ' + obj.re.pattern.decode('utf-8') + " was found.  Setting password to preferred and exiting login function.")
#             device['password'] = device['preferred_password']
#             return obj, output
#         elif idx == 5 or idx == 11:
#             if output.decode('utf-8').find('System Initializing. Please wait to login...') >= 0:
#                 if DEBUG:
#                     print('vManage is still initializing.  Waiting 20 seconds before trying again.')
#                 time.sleep(20)
#             else:
#                 track_incorrect += 1
#                 print('Incorrect Logins: ' + str(track_incorrect))
#                 if track_incorrect >= 2:
#                     if DEBUG:
#                         print('Incorrect login detected.  Updating to preferred password and looping.')
#                     # If login is incorrect, try the preferred_password key on next loop
#                     device['password'] = device['preferred_password']
#         # If we get back 'account locked' or a prompt to select storage (vmanage), exit this routine.
#         elif idx == 7 or idx == 10:
#             if DEBUG:
#                 print('Pattern matched: ' + obj.re.pattern.decode(
#                     'utf-8') + " - Exiting out of login loop.")
#             return obj, output
#         elif idx == 8:
#             if re.search('login:', s) is None:
#                 if DEBUG:
#                     print("Found system ready prompt.  Returning and looping one last time")
#                 telnet_obj.write(b'\n')
#         else:
#             if DEBUG:
#                 print("Didn't find a login prompt.  Looping to try again.")
#             telnet_obj.write(b'\n')
#
#         if track_incorrect >= 2:
#             if DEBUG:
#                 print('Login incorrect.  Updating password to ' + device['preferred_password'])
#             # If login is incorrect, try the preferred_password key on next loop
#             device['password'] = device['preferred_password']


def pre_config_vmanage(telnet_obj):
    prompts = [
        b'Would you like to format vdb? (y/n):',                # 0
        b'Select storage device to use:',                       # 1
        b'System Ready',                                        # 2
        b'The system is going down for reboot NOW!',            # 3
        b'login:',                                              # 4
        b'vmanage#',                                            # 5
    ]
    # Track first run of loop to pass received_output into output
    # first_run = True
    while True:
        idx, obj, output = telnet_obj.expect(prompts, 2)
        # if output is b' ':
        #     if first_run:
        #         output = received_output
        #         obj = received_obj

        s = output.decode()
        if DEBUG:
            print('Looping through pre_config for vManage')
        # If privelege prompt exists, exit this function and return False to parent.
        if idx == 5:
            return False

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
        telnet_obj.write(b"\n")
        idx, obj, output = telnet_obj.expect(prompts, 5)
        if idx == 0 or idx == 1:
            # TODO: Finish this part up.
            print('Logged in.  Beginning to send commands.')
            for line in config:
                telnet_obj.write(line.encode())
            telnet_obj.write(b'exit\n')


def tabulate_devices():
    for device in v_devices:
        details = [device['name'], HOST, device['port']]
        device_details.append(details)

    print('\nThe following default values will be used to initial provision the Viptela POD.\n')
    print(tabulate(device_details, headers=['DEVICE', 'HOST', 'PORT'], tablefmt="pretty"))
    # response = input('Would you like to make changes to these values [y/n]') or 'n'


def ping_host(ip, count=1):
    response = ping(ip, count)
    if (count - response.packets_lost) > 0:
        return True


def main():
    global ALL_COMPLETE

    tabulate_devices()

    while not ALL_COMPLETE:
        for device in v_devices:
            # If device key for is_configured is set to False:
            # Ping the device VPN0 ip.  If it responds, mark as configured.
            # If it does not respond, continue with configuration.
            if not device['is_configured']:
                if ping_host(device['vpn0_ip']):
                    print(device['name'] + ' is active!')
                    device['is_configured'] = True
                else:
                    print(device['name'] + ' is NOT active.  Attempting to configure.')
                    # print(response)
                    config = open(device['initial_config_file'], 'r')
                    config_lines = config.readlines()
                    try:
                        if DEBUG:
                            print('Launching telnet session to ' + HOST + ':' + device['port'])
                        tn = telnetlib.Telnet(HOST, device['port'])
                        # tn.write(b'exit\n')
                        if DEBUG:
                            print('Logging into ' + HOST + ':' + device['port'])
                        # telnet_obj, telnet_output = login_telnet(tn, device)
                        login2(tn, device)
                        if device['name'] == 'vmanage' and not device['is_configured']:
                            if DEBUG:
                                print('Pre-configuring vManage.  This process will take 15-30 minutes')
                            pre_config_exected = pre_config_vmanage(tn)
                            successful = login2(tn, device)
                            if successful:
                                print('Successfully pre-configured vManage.  Moving onto general configuration.')
                            #login_telnet(tn, device)
                        write_config(tn, device, config_lines)
                        print(tn.read_all())
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
    print('All devices configured.  Login to vManage using the MGMT interface IP: PLACEHOLDER') # TODO: Add MGMT IF IP after configuration


main()


