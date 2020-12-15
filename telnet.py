from pythonping import ping
import telnetlib
import time, datetime
from tabulate import tabulate
import re
from threading import Thread, currentThread
import threading
# from classes import multi_threading
from utils import ping_host


class myThread (threading.Thread):

    def __init__(self, name, counter, device, target=None):
        threading.Thread.__init__(self)
        self.threadID = counter
        self.name = name
        self.counter = counter
        self.target = target
        self.device = device

    def run(self):
        print("\nStarting " + self.name)
        #counter(self.name, self.counter)
        configure_viptela_pod(self.device, self.name, self.counter)
        print("Exiting " + self.name)




HOST = '172.28.43.171'
user = 'admin'
password = 'insight'

LOGGED_IN = False
ALL_COMPLETE = False
DEBUG = True

# Create vManage, vBond, and vSmart objects.  Associate default configuration files with each object.  Add to list.

vManage2 = {
    'name': 'vmanage',
    'port': '32793',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.5',
    'is_configured': False,
    'initial_config_file': 'configs/vmanage2-initial.txt',
    'thread_header': '',
    'vpn512_ip': '',
}
vSmart = {
    'name': 'vsmart',
    'port': '32770',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.3',
    'is_configured': False,
    'initial_config_file': 'configs/vsmart-initial.txt',
    'thread_header': '',
    'vpn512_ip': '',
}
vBond = {
    'name': 'vbond',
    'port': '32771',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.2',
    'is_configured': False,
    'initial_config_file': 'configs/vbond-initial.txt',
    'thread_header': '',
    'vpn512_ip': '',
}
vManage = {
    'name': 'vmanage',
    'port': '32769',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.1',
    'is_configured': False,
    'initial_config_file': 'configs/vmanage-initial.txt',
    'thread_header': '',
}

v_devices = [vManage, vManage2, vSmart, vBond]

for device in v_devices:
    device['console_host'] = HOST

device_details = []


def main():
    global ALL_COMPLETE

    tabulate_devices()

    # threads_test()

    while not ALL_COMPLETE:
        threads2()

        track_configured = 0
        for device in v_devices:
            if device['is_configured']:
                track_configured += 1

        tabulate_device_status()

        if track_configured == len(v_devices):
            ALL_COMPLETE = True
    print('All devices configured.  Login to vManage using the MGMT interface IP: PLACEHOLDER') # TODO: Add MGMT IF IP after configuration



def get_mgmt_if(telnet_obj, device):
    if DEBUG:
        print(device['thread_header'] + 'Getting MGMT IP for vManage')
    reply = telnet_obj.write(b'show int | tab')
    reply = reply.split('\n')
    x = 1
    for line in reply:
        if re.search('^(512).*', line) is not None:
            if DEBUG:
                print('Found VPN 512 in line ' + str(x))
            split_line = ' '.join(line.split()).split()
            # split_line = line.split(' ')
            CIDR = split_line[3]
            ipv4 = CIDR.split('/')
            ipv4 = ipv4[0]
            print(ipv4)
            if left(ipv4, 1) == 0:
                print('VMANAGE: GET_VPN512_IP: Invalid IPv4 Address found.  Enter correct IPv4 address to continue.')
            else:

                print('VMANAGE: GET_VPN512_IP: Found IPv4 address ' + ipv4 + '.')
                return ipv4
            x += 1

def threads():
    if DEBUG:
        print('THREADS: Starting multithreading.')
    threads = []
    for device in v_devices:
        if not device['is_configured']:
            if DEBUG:
                print('THREADS: Starting thread for ' + device['name'])
            th = Thread(
                name=device['name'] + '-' + device['port'],
                target=configure_viptela_pod(device)
            )
            th.start()
            threads.append(th)

        # Wait for all threads to finish
        for th in threads:
            th.join()


def threads_test():
    my_list = ['a', 'b', 'c', 'd', 'e', 'f', '1', '2']
    x = 1
    threads = []
    for item in my_list:
        print('Starting thread for ' + item)
        new_thread = myThread(item, x, counter(item, x))
        new_thread.start()
        threads.append(new_thread)
        x += 1

    # Wait for all threads to finish
    for th in threads:
        th.join()
    new_thread.join()


def counter(threadName, counter):
    import time

    x = 0
    while x < 5:
        datefields = []
        today = datetime.date.today()
        datefields.append(today)
        print("{}[{}]: {} - {}".format( threadName, counter, datefields[0], x))
        time.sleep(2)
        x += 1


def threads2():
    if DEBUG:
        print('THREADS: Starting multithreading.')
    threads = []
    x = 1
    for device in v_devices:
        if not device['is_configured']:
            device['thread_header'] = device['name'] + '[' + str(x) + ']' + ': '
            display_name = device['name'] + ':' + device['port']
            if DEBUG:
                print('THREADS: Starting thread for ' +
                      device['name'] + ' (' + HOST + ':' +
                      device['port'] + ') - counter: ' + str(x))

            new_thread = myThread(display_name, x, device)
            new_thread.start()
            threads.append(new_thread)
            x += 1

    # Wait for all threads to finish
    for th in threads:
        th.join()
    new_thread.join()


def configure_viptela_pod(device, thread_name, counter):
    # If device key for is_configured is set to False:
    # Ping the device VPN0 ip.  If it responds, mark as configured.
    # If it does not respond, continue with configuration.
    while not device['is_configured']:
        if ping_host(device['vpn0_ip']):
            print(device['thread_header'] + device['name'] + '(' +
                  device['vpn0_ip'] +
                  ') is active!')
            device['is_configured'] = True

        else:
            print(device['thread_header'] + device['name'] + '(' +
                  device['vpn0_ip'] +
                  ') is NOT active.  Attempting to configure.')
            config = open(device['initial_config_file'], 'r')
            config_lines = config.readlines()
            try:
                if DEBUG:
                    print(device['thread_header'] + 'Launching telnet session to ' + HOST + ':' + device['port'])
                tn = telnetlib.Telnet(HOST, device['port'])
                if DEBUG:
                    print(device['thread_header'] + 'Logging into ' + HOST + ':' + device['port'])
                successful, telnet_idx, telnet_obj, telnet_output = login2(tn, device)
                if device['name'] == 'vmanage' and not device['is_configured']:
                    if DEBUG:
                        print(device['thread_header'] + 'Pre-configuring vManage.  This process will take 15-30 minutes')
                    pre_config_completed = pre_config_vmanage(tn, telnet_idx, telnet_obj, telnet_output)
                    if pre_config_completed:
                        successful = login2(tn, device)
                if successful:
                    print(device['thread_header'] + 'Successfully pre-configured vManage.  Moving onto general configuration.')
                    write_config(tn, device, config_lines)
                    if device['name'] == 'vmanage':
                        # Wait 10 seconds for DHCP to assign IP
                        time.sleep(10)
                        vmanage_vpn512_ip = get_mgmt_if(tn, device)
                        device['vpn512_ip'] = vmanage_vpn512_ip
                print(device['thread_header'] + 'MAIN: Attempted completion of device ' + device['name'] + ' is now completed.')
                if tn.sock:
                    tn.close()
                    print(device['thread_header'] + 'MAIN: Closing telnet connection for device ' + device['name'])
                else:
                    print(device['thread_header'] + 'MAIN: Closing telnet connection for device ' + device['name'])

            except ConnectionRefusedError as error:
                print(device['thread_header'] + 'Connection was refused to ' + HOST + ' on port ' + device['port'] + '.')
            except BrokenPipeError as error:
                print(device['thread_header'] + 'Connection was broken to host: ' + HOST + ' on port ' + device['port'] + '.')
            except EOFError as error:
                print(device['thread_header'] + 'Connection to host was lost: ' + HOST)
            time.sleep(30)


def login2(telnet_obj, device):
    prompts = [
        br'[lL]ogin:',                              # 0
        device['name'].encode('utf-8') + b'#',      # 1
        'vedge'.encode('utf-8') + b'#',             # 2
        b'Password:',                               # 3
        b'Select storage device to use:',           # 4
        b'You must set an initial admin password',  # 5
    ]

    track_incorrect = 0
    save_idx, save_obj, save_output = None, None, None
    login_typed = False
    track_loops = 0
    login_found = False

    while True:
        idx, obj, output = None, None, None
        if save_idx is None:
            time.sleep(5)
            idx, obj, output = telnet_obj.expect(prompts, 5)
        else:
            # If values found outside of while loop, accept those values and reset outside variables
            idx, obj, output = save_idx, save_obj, save_output
            save_idx, save_obj, save_output = None, None, None
        s = output.decode()

        # Search for more complicated patterns that are not working right with telnet expect
        if re.search('System Initializing. Please wait to login...', s) is not None:
            #telnet_obj.write(b'\n')
            print(device['thread_header'] + 'LOGIN: INITIALIZE: vManage is still initializing.  Waiting up to 180 seconds for system to be ready before trying again.')
            return_val = telnet_obj.read_until(b'System Ready', timeout=180)
            if return_val is not b' ':
                time.sleep(3)
                completed_login = False
                print(device['thread_header'] + 'LOGIN: INITIALIZE: vManage is Ready. Logging in now.')
                telnet_obj.write(b'\n')
                while not completed_login:
                    idxx, objx, outputx = telnet_obj.expect(prompts, 5)
                    if idxx == 0:
                        if DEBUG:
                            print(
                                device['thread_header'] +
                                'LOGIN: INITIALIZE: Sending username ' + device['username'] + '.'
                            )
                        telnet_obj.write(device['username'].encode('ascii') + b"\n")
                        # Wait up to 20 seconds for the password prompt.
                        telnet_obj.read_until(b'Password:', 20)
                        if DEBUG:
                            print(
                                device['thread_header'] +
                                'LOGIN: INITIALIZE: Sending password ' + device['password'] + '.'
                            )
                        telnet_obj.write(device['password'].encode('ascii') + b"\n")
                        idxx, objx, outputx = telnet_obj.expect(prompts, 5)
                        sx = outputx.decode()

                        # Search for more complicated patterns that are not working right with telnet expect
                        if re.search('Login incorrect', sx) is not None:
                            # if login incorrect found, increment tracker to change password faster
                            # and pass telnet_object data to top of loop
                            track_incorrect += 1
                        save_idx = idxx
                        save_obj = objx
                        save_output = outputx
                        if DEBUG:
                            print(
                                device['thread_header'] +
                                'LOGIN: INITIALIZE: Login complete.  Exiting loop.'
                            )
                        completed_login = True
                    elif idxx == 3:
                        telnet_obj.write(b'\n')
        elif re.search('Login incorrect', s) is not None:
            track_incorrect += 1
            print(device['thread_header'] + 'LOGIN: LOGIN_INCORRECT: Incorrect Logins: ' + str(track_incorrect))
            # If incorrect password, save telnet object info and send back to top of the loop.
            # The 'login:' prompt exists in the output and we need to key on it without sending CR
            save_idx = idx
            save_obj = obj
            save_output = b'login:'
        # if pattern matches initial password or idx == 6, do the following:
        elif re.search('You must set an initial admin password', s) is not None or idx == 5:
            if DEBUG:
                print(device['thread_header'] + 'LOGIN: SET_PASS: Setting initial admin passwords')
            # If initial setup prompted, send new password.
            match_passwords(telnet_obj, device, device['preferred_password'])
            x = 1
        # If login prompt found, send username followed by password
        elif idx == 0:
            if DEBUG:
                print(device['thread_header'] +
                      'LOGIN: Pattern matched: ' + obj.re.pattern.decode('utf-8') +
                      '.  Found login prompt.  Sending username ' +
                      device['username']
                )
            telnet_obj.write(device['username'].encode('ascii') + b"\n")
            login_typed = True
            login_found = True
        elif idx == 3:
            if login_typed:
                if DEBUG:
                    print(device['thread_header'] +
                          'LOGIN: Pattern matched: ' +
                          obj.re.pattern.decode('utf-8') +
                          '.  Sending password ' + device['password']
                          )
                telnet_obj.write(device['password'].encode('ascii') + b"\n")
                login_typed = False
            else:
                telnet_obj.write(b"\n")

                # If we are at password prompt, but login hasn't been typed, press enter.
        # If privilege mode prompt found, exit function
        elif idx == 1 or idx == 2:
            if DEBUG:
                print(
                    device['thread_header'] + 'LOGIN: Found privilege prompt.  Exiting function.'
                )
            return True, idx, obj, output
        # Found storage device prompt.  Exiting function.
        elif idx == 4:
            if DEBUG:
                print(
                    device['thread_header'] + 'LOGIN: Found storage device prompt.  Exiting function.'
                )
            return True, idx, obj, output
        else:
            if login_found:
                track_loops += 1
                if track_loops >= 3 and login_found:
                    print(device['thread_header'] + 'Something is wrong with the loop')
            telnet_obj.write(b'\n')
            if DEBUG:
                print(device['thread_header'] + 'LOGIN: Login prompt not found.  Looping function.')

        if track_incorrect == 2:
            device['password'] = device['preferred_password']
            if DEBUG:
                print(device['thread_header'] + 'Incorrect password 2 times.  Updating password to preferred password: ' +
                      device['preferred_password'])


def match_passwords(telnet_obj, device, new_password):
    passwords_match = False

    while not passwords_match:
        telnet_obj.write(new_password.encode('ascii') + b'\n')
        telnet_obj.read_until(b'Re-enter password:', 20)
        telnet_obj.write(new_password.encode('ascii') + b'\n')

        prompts = [
            b'Try again...',
            b'#',
            b'Select storage device to use:',
        ]

        idx, obj, output = telnet_obj.expect(prompts, 15)

        if idx == 0:
            if DEBUG:
                print(device['thread_header'] + "Passwords don't match. Try again.")
        else:
            device['password'] = device['preferred_password']

        # Finish checking for matches.
        if idx == 1:
            if DEBUG:
                print(device['thread_header'] + "Passwords matched and were accepted.  Continuing")
            passwords_match = True
        elif idx == 2:
            if DEBUG:
                print(device['thread_header'] + "Passwords matched and were accepted.  Prompt for vmanage pre-config.")
            passwords_match = True
    return True


def format_time(input):
    input_str = str(input).split('.')[0]

    if len(input_str) != 2:
        output = str(0) + str(input_str)
        output = str(output)
    else:
        output = input_str
    return output


def wait_timer(message, telnet_obj, device, wait_string, interval=30, max_time=3600):
    start_time = time.time()
    time_delta = 0
    hours = '00'
    minutes = '00'
    seconds = '00'
    beginning_max_time = max_time

    wait_string_str = ''
    if isinstance(wait_string, bytes):
        wait_string_str = wait_string.decode()
    else:
        wait_string_str = wait_string

    print(message)
    print(device['thread_header'] + 'Maximum timeout: ' + str(max_time))
    print(device['thread_header'] + 'Poll interval: ' + str(interval))
    print('', end='\r')
    print(device['thread_header'] + 'Elapsed Time: ' + str(hours) + ':' + str(minutes) + ':' + str(seconds), end=' ')
    # Check to see if max timer has expired
    while max_time > 0:
        if max_time - interval < 0:
            interval = max_time
        max_time = beginning_max_time
        output = telnet_obj.read_until(wait_string, interval)
        s = output.decode()
        if re.search(wait_string_str, s) is not None:
            max_time = 0
            return True
        now_time = time.time()
        time_delta = int(now_time - start_time)
        max_time = max_time - time_delta
        if time_delta >= 3600:
            hours = format_time(time_delta // 3600)
            time_delta = time_delta - int(hours) * 3600
        if time_delta >= 60:
            minutes = format_time(time_delta // 60)
            time_delta = time_delta - int(minutes) * 60

        seconds = format_time(time_delta)
        print('', end='\r')
        print(device['thread_header'] + 'Elapsed Time: ' + str(hours) + ':' + str(minutes) + ':' + str(seconds), end=' ')
    print('\n' + device['thread_header'] + 'Time has elapsed on the wait timer function.')
    return False


def pre_config_vmanage(telnet_obj, input_idx, input_obj, input_output):
    prompts = [
        b'Would you like to format vdb? (y/n):',                # 0
        b'Select storage device to use:',                       # 1
        b'System Ready',                                        # 2
        b'The system is going down for reboot NOW!',            # 3
        b'login:',                                              # 4
        b'vmanage#',                                            # 5
    ]
    # Track first run of loop to pass received_output into output
    first_run = True
    while True:
        idx, obj, output = None, None, None
        if first_run:
            idx = input_idx
            obj = input_obj
            output = input_output
            first_run = False
        else:
            idx, obj, output = telnet_obj.expect(prompts, 2)

        s = output.decode()
        if DEBUG:
            print(device['thread_header'] + 'Looping through pre_config for ' + device['name'] + ':' + device['port'])
        # If privelege prompt exists, exit this function and return False to parent.
        if idx == 5:
            return False

        if re.search('Would you like to format vdb?', s):
            if DEBUG:
                print(device['thread_header'] + 'Pattern matched for formatting vdb: Responding with ''y''.')
            telnet_obj.write(b'y\n')
            # Reboot will take 30+ minutes to complete.  Set timer at 40 minutes and watch for 'System Ready' message
            print(device['thread_header'] +
                  'PRE-CONFIG:VMANAGE: vManage needs to prepare the hard drive and reboot.  '
                  'This process could take from between 10 and 60 minutes.')

            timer_response = wait_timer('Waiting for vManage to start reboot.  DO NOT SHUT DOWN VMANAGE.',
                       telnet_obj, device, b'Restarting system', 5, 1200)
            if timer_response:
                print('\n' + device['thread_header'] + 'PRE-CONFIG:VMANAGE:SUCCESS: Reboot is starting')
            else:
                print(device['thread_header'] + 'PRE-CONFIG:VMANAGE:FAILURE: vManage reboot is not starting as expected.')

            timer_response = wait_timer('Waiting for vManage to build HDD and reboot.  DO NOT SHUT DOWN VMANAGE.',
                       telnet_obj, device, b'System Ready', 5)
            if timer_response:
                print('\n' + device['thread_header'] + 'PRE-CONFIG:VMANAGE:SUCCESS: HDD Build on vManage is complete.  Continuing with configuration.')
            else:
                print('\n' + device['thread_header'] + 'PRE-CONFIG:VMANAGE:FAILURE: Investigate HDD configuration with vManage.')
            return True
        elif re.search('Select storage device to use:', s):
            if DEBUG:
                print(device['thread_header'] + 'Pattern matched for selecting device: Selected vdb as storage device.')
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

    max_retry = 3
    i = 0

    while i <= max_retry:
        telnet_obj.write(b"\n")
        idx, obj, output = telnet_obj.expect(prompts, 5)
        if idx == 0 or idx == 1:
            # TODO: Finish this part up.
            print(device['thread_header'] + 'WRITE_CONFIG: Beginning to send commands.')
            for line in config:
                telnet_obj.write(line.encode())
            output = telnet_obj.expect(prompts, 60)
            if output is not b'':
                print('WRITE_CONFIG: Finished sending commands.  Leaving function.')
                is_config_applied = True
                i = max_retry + 1
            else:
                print(device['thread_header'] + 'WRITE_CONFIG: Error sending commands.  Trying again.')
                i += 1
                time.sleep(5)

    return True


def tabulate_devices():
    for device in v_devices:
        details = [device['name'], HOST, device['port']]
        device_details.append(details)

    print('\nThe following default values will be used to initial provision the Viptela POD.\n')
    print(tabulate(device_details, headers=['DEVICE', 'HOST', 'PORT'], tablefmt="pretty"))
    # response = input('Would you like to make changes to these values [y/n]') or 'n'


def tabulate_device_status():
    status = []
    for device in v_devices:
        is_configured = ""
        if device['is_configured']:
            is_configured = 'Complete'
        else:
            is_configured = 'Pending'
        details = [device['name'], device['vpn0_ip'], is_configured]
        status.append(details)

    print('\nViptela Provisioning - Current Status.\n')
    print(tabulate(status, headers=['DEVICE', 'VPN0 IP', 'STATUS'], tablefmt="pretty"))


def left(s, amount):
    return s[:amount]

def right(s, amount):
    return s[-amount:]

def mid(s, offset, amount):
    return s[offset:offset+amount]



main()


