from pythonping import ping
import telnetlib
import time, datetime
from tabulate import tabulate
import re
from threading import Thread, currentThread
import threading
# from classes import multi_threading
from utils import ping_host
from netmiko import ConnectHandler, SSHDetect, NetmikoAuthenticationException, NetmikoTimeoutException, file_transfer
from classes.viptela_rest import vmanage_lib
import json
import os
import paramiko
from paramiko import SSHClient
from scp import SCPClient
import socket
from requests.packages.urllib3.exceptions import MaxRetryError, InsecureRequestWarning
import requests
import sys
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
from vmanage.cli.certificate.install import install as cert_install
from vmanage.api.certificate import Certificate
from vmanage.api.settings import Settings
from vmanage.api.authentication import Authentication
from vmanage.api.utilities import Utilities
from vmanage.api.device import Device
import ipaddress


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
        configure_viptela_pod(self.device, self.name, self.counter)
        print("Exiting " + self.name)


HOST = '172.28.43.171'
user = 'admin'
password = 'insight'

LOGGED_IN = False
ALL_COMPLETE = False
DEBUG = True

if DEBUG:
    paramiko.util.log_to_file('ssh.log')

# Create vManage, vBond, and vSmart objects.  Associate default configuration files with each object.  Add to list.

vSmart = {
    'name': 'vsmart',
    'port': '32770',
    'system_ip': '1.1.1.3',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.3',
    'is_configured': False,
    'initial_config_file': 'configs/vsmart-initial.txt',
    'post_config_file': 'configs/vsmart-post.txt',
    'thread_header': '',
    'vpn512_ip': '',
    'CSR': '',
    'CRT': '',
    'ssh_obj': None,
}
vBond = {
    'name': 'vbond',
    'port': '32771',
    'system_ip': '1.1.1.2',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.2',
    'is_configured': False,
    'initial_config_file': 'configs/vbond-initial.txt',
    'post_config_file': 'configs/vbond-post.txt',
    'thread_header': '',
    'vpn512_ip': '',
    'CSR': '',
    'CRT': '',
    'ssh_obj': None,
}
vManage = {
    'name': 'vmanage',
    'port': '32769',
    'system_ip': '1.1.1.1',
    'console_host': '',
    'username': 'admin',
    'password': 'admin',
    'preferred_password': 'insight',
    'vpn0_ip': '51.51.51.1',
    'is_configured': False,
    'initial_config_file': 'configs/vmanage-initial.txt',
    'thread_header': '',
    'vpn512_ip': '',
    'root_ca_cert': '',
    'CSR': '',
    'CRT': '',
    'provisioned': '',
    'ssh_obj': None,
}

v_devices = [vManage, vSmart, vBond]

for device in v_devices:
    device['console_host'] = HOST

device_details = []


def main():
    global ALL_COMPLETE

    tabulate_devices()

    while not ALL_COMPLETE:
        threads2()

        track_configured = 0
        for device in v_devices:
            if device['is_configured']:
                track_configured += 1

        tabulate_device_status()

        if track_configured == len(v_devices):
            ALL_COMPLETE = True
        print('All threads for pre-configure are completed.  Moving onto vManage configuration.')
    for device in v_devices:
        if left(device['name'], 7) == 'vmanage':
            print(
                'MAIN: All devices configured.  Login to vManage using the MGMT interface IP: ' + device['vpn512_ip'] + '.')
            connect_success = False
            try:
                connect_success = ssh_connect(device)
            except NetmikoAuthenticationException as error:
                print('MAIN: Authentication failed to ' + device['name'] + ':' + device[
                    'port'] + ' on VPN512 IP address ' + device['vpn512_ip'])
            except NetmikoTimeoutException as error:
                print('MAIN: Connection timed out to ' + device['name'] + ':' + device[
                    'port'] + ' on VPN512 IP address ' + device['vpn512_ip'])
            if connect_success:
                vmanage_ssh_config(device)
            provisioned = False
            is_up = False
            while not provisioned:
                # Check that host is up on VPN 512, responding to TCP/8443, and renders correct webpage.
                is_up = False
                while not is_up:
                    if wait_timer('\nWaiting for ICMP to reply', device, function='ping_device', interval=5):
                        if wait_timer('\nWaiting for TCP/8443 to reply', device, function='check_socket', interval=5):
                            if wait_timer('\nWaiting for webpage to render', device, function='check_vmanage_webpage', interval=5):
                                print('HTML page is rendered and shows login.  ip_up set to true')
                                is_up = True
                                break
                            else:
                                time.sleep(10)
                        else:
                            time.sleep(10)
                print('MAIN: vManage is responding to pings, port 8443 is open, and HTML page is being rendered.  '
                      'Continuing to provision device via API.')
                provisioned = provision_vmanage_initial2(device)

    if provisioned:
        for device in v_devices:
            if left(device['name'], 5) == 'vbond' or left(device['name'], 5) == 'vsmar':
                if DEBUG:
                    print('Finalizing ' + device['name'] + ' configuration.')
                try:
                    ssh_connect(device, device['vpn0_ip'])
                except NetmikoAuthenticationException as error:
                    print('MAIN: Authentication failed to ' + device['name'] + ':' + '22' + ' on VPN0 IP address ' + device['vpn0_ip'])
                except NetmikoTimeoutException as error:
                    print('MAIN: Connection timed out to ' + device['name'] + ':' +
                          '22 on VPN0 IP address ' + device['vpn0_ip'])
                ssh_obj = device['ssh_obj']
                if ssh_obj is not None:

                    config = open(device['post_config_file'], 'r')
                    config_lines = config.readlines()
                    for line in config_lines:
                        ssh_obj.send_command(line, expect_string=device['name'] + r'.*#')
                    ssh_obj.disconnect()
                else:
                    print('FAILED: Skipped post-configuration of ' + device['name'] + ' because SSH failed. ')
            print('Finished configuration for ' + device['name'])


    # TODO: Cleanup files created
    # TODO: Exit telnet sessions
    # TODO: Loop continuously so it can persistently run in backgroun.
    # TODO: Check for things like ORG name, vbond, etc before changing them.  Get all values, then if values dont' exist, add.

def check_vmanage_webpage(device):
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    url = 'https://%s:8443' % device['vpn512_ip']

    try:
        response = requests.get(url, verify=False)

        if re.search('j_username', response.text) is not None:
            print('Found username form in vManage webpage.')
            return True
        else:
            return False
    except MaxRetryError as error:
        return False
    except:
        return False


def check_socket(device):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    location = (device['vpn512_ip'], 8443)
    result = a_socket.connect_ex(location)

    if result == 0:
        print('\nPort 8443 for vManage is open and responding to requests.')
        return True
    else:
        return False


def provision_vmanage_initial2(device):
    if DEBUG:
        print('TESTING: Starting initial vManage configuration via API.')

    # Instantiate session and login.
    vmanage_sess = Authentication(host=device['vpn512_ip'], user=device['username'], password=device['preferred_password'],
                          port=8443, validate_certs=False, timeout=20).login()

    # Create new token for additional configuration that isn't included in API
    vmanage_sess2 = vmanage_lib(device['vpn512_ip'], device['username'], device['preferred_password'])

    # Instantiate all classes that we will need to use.  Login, Settings, Certificate, Device, Utilities
    # vmanage_sess = vmanage_sess.login()
    vmanage_settings = Settings(vmanage_sess, device['vpn512_ip'])
    vmanage_certificate = Certificate(vmanage_sess, device['vpn512_ip'])
    vmanage_device = Device(vmanage_sess, device['vpn512_ip'])
    vmanage_utilities = Utilities(vmanage_sess, device['vpn512_ip'])

    result = ""
    vmanage_configured = False
    vbond_configured = False
    vsmart_configured = False

    # Set organization Name
    organization = 'DEFAULT - 155893'
    if DEBUG:
        print('Setting vmanage organization name to ' + organization + '.')
    try:
        result = vmanage_settings.set_vmanage_org(organization)
        print('SUCCESS: Setting vmanage organization name to ' + organization + '.')
    except Exception as e:
        print(e)

    # Set vbond IP address in Administration -> Settings
    vbond_ip = '51.51.51.2'
    vbond_port = 12346
    try:
        result = vmanage_settings.set_vmanage_vbond(vbond_ip, vbond_port)
        print('SUCCESS: set vbond IP in settings to ' + vbond_ip + ':' + str(vbond_port))
    except Exception as e:
        print(e)

    # Set Certificate Authority to Enterprise
    try:
        result = vmanage_settings.set_vmanage_ca_type('enterprise')
        print('SUCCESS: set Certificate Authority to ''enterprise''')
    except Exception as e:
        print(e)

    # Import enterprise ROOTCA.pem file into Administration -> certificates
    if DEBUG:
        print('Importing enterprise ROOTCA.pem file into vManage.')
    data = device['root_ca_cert']
    try:
        vmanage_settings.set_vmanage_root_cert(data)
        print('SUCCESS: Importing ROOTCA.pem file into vManage.')
    except Exception as e:
        print(e)

    # Determine if vmanage, vsmart, and vbond are already configured
    try:
        response = vmanage_device.get_device_list('controllers')
        for item in response:
            if item['deviceIP'] == device['system_ip'] or item['deviceIP'] == device['vpn0_ip']:
                if item['serialNumber'] != '' and item['serialNumber'] != 'No certificate installed':
                    print('vManage has had a certificate installed.  Skipping CSR generation, sign, and import.')
                    vmanage_configured = True
            elif item['deviceIP'] == vBond['system_ip'] or item['deviceIP'] == vBond['vpn0_ip']:
                if item['serialNumber'] != '' and item['serialNumber'] != 'No certificate installed':
                    print('vBond has had a certificate installed.  Skipping CSR generation, sign, and import.')
                    vbond_configured = True
            elif item['deviceIP'] == vSmart['system_ip'] or item['deviceIP'] == vSmart['vpn0_ip']:
                if item['serialNumber'] != '' and item['serialNumber'] != 'No certificate installed':
                    print('vSmart has had a certificate installed.  Skipping CSR generation, sign, and import.')
                    vsmart_configured = True

    except Exception as e:
        print(e)

    if not vmanage_configured:
        # Generate CSR for vmanage
        if DEBUG:
            print('Generating CSR for vManage.')
        data = device['system_ip']
        try:
            vmanage_certificate.generate_csr(data)
            print('SUCCESS: Generated CSR for vManage ' + device['system_ip'])
        except Exception as e:
            print('FAILED: ' + e)

        # Get CSR for vManage
        if DEBUG:
            print('Getting CSR for vManage and writing to file.')
        try:
            response = vmanage_device.get_device_list('controllers')
            for item in response:
                if item['deviceIP'] == device['system_ip']:
                    device['CSR'] = item['deviceCSR'].strip()
                    print('SUCCESS: Generated new CSR: \n' + device['CSR'])
        except Exception as e:
            print(e)

        # Sign CSR on vshell
        if DEBUG:
            print('Sign CSR for vManage on vshell console')

        vmanage_sign = 'openssl x509 -req -in vmanage_csr -CA ROOTCA.pem -CAkey \
         ROOTCA.key -CAcreateserial -out vmanage.crt -days 2000 -sha256'
        try:
            reply = vshell_config(device, vmanage_sign)
            print('SUCCESS:  Signed CSR on vshell.')
        except Exception as e:
            print(e)

        # Copy vmanage CRT into dictionary
        device['CRT'] = vshell_config(device, 'cat vmanage.crt')

        # Import the vmanage CRT into application
        if DEBUG:
            print('Import vManage CRT into vManage')
        try:
            reply = vmanage_certificate.install_device_cert(device['CRT'])
            print('SUCCESS: Imported vManage CRT.')
        except Exception as e:
            print(e)

    # Add vbond to devices
    if not vbond_configured:
        if DEBUG:
            print('Adding vbond device to vmanage application.')
        payload = {
            "deviceIP": "51.51.51.2",
            "username": "admin",
            "password": "insight",
            "personality": "vbond",
            "generateCSR": True
        }
        try:
            response = vmanage_sess2.run_api('system/device', payload, method='post')
            print('SUCCESS: Added vbond device ' + vBond['system_ip'])
        except:
            print('FAILED: Cannot add vbond device: ' + device['vpn512_ip'] + '.')

        device_list = ""
        print('Waiting 30 seconds for CSR to be generated.')
        time.sleep(30)

        try:
            device_list = vmanage_device.get_device_list('controllers')
            print('SUCCESS:  Retrieved list of controllers to parse for CSRs from vmanage.')
        except Exception as e:
            print('FAILED: Unable to get device list to scan for vBond CSR.')

        if isinstance(device_list, list):
            for item in device_list:
                if 'deviceIP' in item:
                    if item['deviceIP'] == vBond['system_ip'] or item['deviceIP'] == vBond['vpn0_ip']:
                        vBond['CSR'] = item['deviceCSR'].strip()
                        if vBond['CSR'] != '':
                            print('SUCCESS: Found vBond CSR.')

        if vBond['CSR'] != '':
            # Write the CSR to file so we can SCP it to sign on vmanage
            print('Write vBond CSR to file.')
            file_obj = open(r'vbond.csr', 'w')
            file_obj.write(vBond['CSR'])
            file_obj.close()

            # Upload the certificates to vManage via SFTP
            copy_file(device, source_file='vbond.csr')

            # Sign vbond and vsmart certs
            vbond_sign = '''
            openssl x509 -req -in vbond.csr \
            -CA ROOTCA.pem -CAkey ROOTCA.key -CAcreateserial \
            -out vbond.crt -days 2000 -sha256
            \n
            '''

            response = vshell_config(device, vbond_sign)

            # Get vbond CRT created in previous step
            vBond['CRT'] = vshell_config(device, 'cat vbond.crt')

            # Import the vbond CRT into application
            if DEBUG:
                print('Import vBond CRT into vManage.')
            try:
                reply = vmanage_certificate.install_device_cert(vBond['CRT'])
                print('SUCCESS: Imported vBond CRT.')
            except Exception as e:
                print('FAILED: ', end='')
                print(e)
        else:
            print('Unable to read CSR for vSmart.  Import certificates manually.')

    # If vsmart not configured, create CSR, sign, and import certificate into vmanage.
    if not vsmart_configured:
        # Add vsmart to devices
        if DEBUG:
            print('Adding vsmart device to vmanage application.')
        payload = {
            "deviceIP": "51.51.51.3",
            "username": "admin",
            "password": "insight",
            "protocol": "DTLS",
            "personality": "vsmart",
            "generateCSR": True
        }
        try:
            response = vmanage_sess2.run_api('system/device', payload, method='post')
            print('SUCCESS: Added vsmart device: ' + device['vpn512_ip'] + '.')
        except:
            print('FAILED: Cannot add vsmart device: ' + device['vpn512_ip'] + '.')

        # Get vSmart CSR
        device_list = ""
        print('Waiting 30 seconds for CSR to be generated.')
        time.sleep(30)
        try:
            device_list = vmanage_device.get_device_list('controllers')
            print('SUCCESS:  Retrieved list of controllers to parse for CSRs from vmanage.')
        except Exception as e:
            print('FAILED: Unable to get device list to scan for vSmart CSR.')

        if isinstance(device_list, list):
            for item in device_list:
                if 'deviceIP' in item:
                    if item['deviceIP'] == vSmart['system_ip'] or item['deviceIP'] == vSmart['vpn0_ip']:
                        vSmart['CSR'] = item['deviceCSR'].strip()
                        if vSmart['CSR'] != '':
                            print('SUCCESS: Found vSmart CSR.')
        response = ""
        try:
            response = vmanage_device.get_device_list('controllers')
        except Exception as e:
            print('FAILED: Unable to get device list to scan for vSmart CSR.')

        if isinstance(device_list, dict):
            for item in response:
                if 'deviceIP' in item:
                    if item['deviceIP'] == vSmart['system_ip'] or item['deviceIP'] == vSmart['vpn0_ip']:
                        vSmart['CSR'] = item['deviceCSR'].strip()
                        if vSmart['CSR'] != '':
                            print('SUCCESS: Found vSmart CSR.')

        if vSmart['CSR'] != '':
            print('Write vSmart CSR to file.')
            file_obj = open(r'vsmart.csr', 'w')
            file_obj.write(vSmart['CSR'])
            file_obj.close()

            # Upload the certificates to vManage via SFTP
            copy_file(device, source_file='vsmart.csr')

            # Sign vsmart certs
            vsmart_sign = '''
            openssl x509 -req -in vsmart.csr \
            -CA ROOTCA.pem -CAkey ROOTCA.key -CAcreateserial \
            -out vsmart.crt -days 2000 -sha256
            \n
            '''
            vshell_config(device, vsmart_sign)

            # Get vSmart CRT created in previous step
            vSmart['CRT'] = vshell_config(device, 'cat vsmart.crt')

            # Import the vsmart CRT into application
            if DEBUG:
                print('Import vSmart CRT into vManage.')
            try:
                reply = vmanage_certificate.install_device_cert(vSmart['CRT'])
                print('SUCCESS: Imported vSmart CRT.')
            except Exception as e:
                print(e)
        else:
            print('Unable to read CSR for vSmart.  Import certificates manually.')

    # Upload WAN Edge file
    data = 'DEFAULT - 155893.viptela'
    try:
        response = vmanage_utilities.upload_file(data)
        print('SUCCESS: Uploaded WAN edge file ' + data + '.')
    except Exception as e:
        print('FAILED: Unable to upload the WAN edge file.')

    device['provisioned'] = True

    return True


def copy_file(device, method="SFTP", source_file=None, dest_file=None):
    if dest_file is None:
        dest_file = source_file

    transport = paramiko.Transport(device['vpn512_ip'], 22)
    transport.connect(username=device['username'], password=device['preferred_password'])

    sftp = paramiko.SFTPClient.from_transport(transport)

    sftp.put(source_file, dest_file)
    sftp.close()
    transport.close()
    if DEBUG:
        print('Finished uploading file ' + source_file)


def vshell_config(v_device, command):
    ssh_obj = v_device['ssh_obj']

    reply = ssh_obj.send_command('vshell', expect_string='$')

    reply = ssh_obj.send_command(command, expect_string='$')
    print(reply)
    return reply


def vmanage_sign_certs(device):
    new_device = {
        'device_type': 'generic',
        'host': device['vpn512_ip'],
        'username': device['username'],
        'password': device['password'],
    }

    net_connect = ConnectHandler(**new_device)
    print('Found the prompt to ' + device['name'] + ':' + device['port'] + ' - ' + net_connect.find_prompt())
    # reply = net_connect.send_command('vshell', expect_string=device['name'] + ':~$')
    shell_name = device['name'] + ':~$'
    reply = net_connect.send_command('vshell', expect_string='$')


    vbond_sign = '''
    openssl x509 -req -in vbond.csr \
    -CA ROOTCA.pem -CAkey ROOTCA.key -CAcreateserial \
    -out vbond.crt -days 2000 -sha256
    '''
    vsmart_sign = '''
    openssl x509 -req -in vsmart.csr \
    -CA ROOTCA.pem -CAkey ROOTCA.key -CAcreateserial \
    -out vsmart.crt -days 2000 -sha256
    '''

    reply += net_connect.send_command(vbond_sign)
    reply += net_connect.send_command(vsmart_sign)
    print(reply)
    net_connect.disconnect()


def ssh_connect(device, host=''):
    new_device = {
        'device_type': 'generic',
        'host': device['vpn512_ip'],
        'username': device['username'],
        'password': device['preferred_password'],
    }
    if host != '':
        new_device['host'] = host

    device['ssh_obj'] = ConnectHandler(**new_device)

    return True


def vmanage_ssh_config(device):
    dir_listing = vshell_config(device, 'ls -al')
    dir_listing = dir_listing.split('\n')
    key_exist = False
    pem_exist = False

    for line in dir_listing:
        if re.search('ROOTCA.key', line) is not None:
            print('ROOTCA.key file already exists.  Skipping key creation.')
            key_exist = True
        elif re.search('ROOTCA.pem', line) is not None:
            print('ROOTCA.pem file already exists.  Skipping pem creation.')
            pem_exist = True
    if not key_exist:
        if DEBUG:
            print('Generating ROOTCA.key file')
        generate_root_ca_key = 'openssl genrsa -out ROOTCA.key 2048'
        reply = vshell_config(device, generate_root_ca_key)
        print(reply)

    if not pem_exist:
        if DEBUG:
            print('Generating ROOTCA.pem file')
        cert_req = '''openssl req -x509 -new -nodes -key ROOTCA.key -sha256 -days 2000 -subj \
        "/C=AU/ST=NSW/L=NSW/O=sdwan-testlab/CN=vmanage.lab" -out ROOTCA.pem
        '''
        reply = vshell_config(device, cert_req)
        print(reply)

    if DEBUG:
        print('Getting contents of ROOTCA.pem')
    vshell_config(device, '\n')
    reply = vshell_config(device, 'cat ROOTCA.pem')
    device['root_ca_cert'] = reply


def get_mgmt_if(telnet_obj, device):
    prompts = [
        device['name'].encode('utf-8') + b'#',
        'vedge'.encode('utf-8') + b'#',
    ]
    retries = 5

    while retries > 0:
        x = 1
        telnet_obj.write(b'show int | tab | include 512\n')
        reply = telnet_obj.read_until(device['name'].encode('utf-8') + b'#', timeout=10).decode()
        reply = reply.split('\n')
        for line in reply:
            if re.search('^(512).*', line) is not None:
                if DEBUG:
                    print('Found VPN 512 in line ' + str(x))
                split_line = ' '.join(line.split()).split()
                # split_line = line.split(' ')
                CIDR = split_line[3]
                ipv4 = CIDR.split('/')
                ipv4 = ipv4[0]
                try:
                    network = ipaddress.IPv4Network(ipv4)
                except ValueError:
                    if DEBUG:
                        print(device['thread_header'] + ' GET_VPN512_IP: Did not find a valid IPv4 address for vpn512.  Trying again.')
                    retries -= 1
                    time.sleep(15)
                    continue
                if left(ipv4, 7) == '0.0.0.0':
                    if DEBUG:
                        print(device['thread_header'] + ' GET_VPN512_IP: IP 0.0.0.0 found, which is not valid.  Trying again.')

                    retries -= 1
                    print(str(retries) + ' retries left.')
                    time.sleep(15)
                    continue
                else:
                    return True, ipv4
                x += 1

    # If no IPv4 found, return false and blank data
    return False, ''


def get_mgmt_if_old(telnet_obj, device):
    if DEBUG:
        print(device['thread_header'] + 'Getting MGMT IP for vManage')
    retry = 5

    while retry > 0:
        telnet_obj.write(b'show int | tab | include 512\n')
        reply = telnet_obj.read_until(device['name'].encode('ascii') + b'#', 5).decode()
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
                if left(ipv4, 1) == 0:
                    print('VMANAGE: GET_VPN512_IP: Invalid IPv4 Address found.  Enter correct IPv4 address to continue.')
                else:

                    print('VMANAGE: GET_VPN512_IP: Found IPv4 address ' + ipv4 + '.')
                    is_mgmt_ip_found = True
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
            print('\n' + device['thread_header'] + device['name'] + '(' +
                  device['vpn0_ip'] + ') is active!')
            device['is_configured'] = True

        else:
            print('\n' + device['thread_header'] + device['name'] + '(' +
                  device['vpn0_ip'] +
                  ') is NOT active.  Attempting to configure.')
            config = open(device['initial_config_file'], 'r')
            config_lines = config.readlines()
            try:
                if DEBUG:
                    print('\n' + device['thread_header'] + 'Launching telnet session to ' + HOST + ':' + device['port'])
                tn = telnetlib.Telnet(HOST, device['port'])
                if DEBUG:
                    print('\n' + device['thread_header'] + 'Logging into ' + HOST + ':' + device['port'])
                successful, telnet_idx, telnet_obj, telnet_output = login2(tn, device)
                if device['name'] == 'vmanage' and not device['is_configured']:
                    if DEBUG:
                        print('\n' + device['thread_header'] + 'Pre-configuring vManage.  This process will take 15-30 minutes')
                    pre_config_completed = pre_config_vmanage(device, tn, telnet_idx, telnet_obj, telnet_output)
                    if pre_config_completed:
                        successful = login2(tn, device)
                if successful:
                    print('\n' + device['thread_header'] + 'Successfully pre-configured vManage.  Moving onto general configuration.')
                    write_config(tn, device, config_lines)
                    if device['name'] == 'vmanage':
                        # Wait 10 seconds for DHCP to assign IP
                        time.sleep(10)
                        mgmt_success, device['vpn512_ip'] = get_mgmt_if(tn, device)
                        if mgmt_success:
                            print('VMANAGE: GET_VPN512_IP: Found IPv4 address ' + device['vpn512_ip'] + '.')
                        else:
                            print('VMANAGE: GET_VPN512_IP: Could not find IPv4 Address.')
                    tn.close()
                print('\n' + device['thread_header'] + 'MAIN: Attempted completion of device ' + device['name'] + ' is now completed.')
                if tn.sock:
                    tn.close()
                    print('\n' + device['thread_header'] + 'MAIN: Closing telnet connection for device ' + device['name'])
                else:
                    print('\n' + device['thread_header'] + 'MAIN: Closing telnet connection for device ' + device['name'])

            except ConnectionRefusedError as error:
                print('\n' + device['thread_header'] + 'Connection was refused to ' + HOST + ' on port ' + device['port'] + '.')
            except BrokenPipeError as error:
                print('\n' + device['thread_header'] + 'Connection was broken to host: ' + HOST + ' on port ' + device['port'] + '.')
            except EOFError as error:
                print('\n' + device['thread_header'] + 'Connection to host was lost: ' + HOST)
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
                print(device['thread_header'] + 'LOGIN: INITIALIZE: ' + device['name'] +
                      ' is ready. Logging in now.')
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


def wait_timer(message, device, wait_string='', telnet_obj=None, interval=30, max_time=3600, function=''):
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
        result = False
        if max_time - interval < 0:
            interval = max_time
        max_time = beginning_max_time
        if telnet_obj is not None:
            output = telnet_obj.read_until(wait_string, interval)
            s = output.decode()
            if re.search(wait_string_str, s) is not None:
                max_time = 0
                return True
        if function == 'check_socket':
            result = check_socket(device)
            if result:
                return True
        elif function == 'check_vmanage_webpage':
            result = check_vmanage_webpage(device)
            if result:
                return True
        elif function == 'ping_device':
            result = ping_device(device)
            if result:
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
        print('\r' + device['thread_header'] + 'Elapsed Time: ' + str(hours) + ':' + str(minutes) + ':' + str(seconds), end=' ')
        if telnet_obj is None:
            time.sleep(interval)
    print('\n' + device['thread_header'] + 'Time has elapsed on the wait timer function.')

    return False


def ping_device(device):
    icmp = ping(device['vpn512_ip'], count=1)
    if icmp.packets_lost == 0.0:
        print('\nHost is online.')
        return True
    else:
        return False



def pre_config_vmanage(device, telnet_obj, input_idx, input_obj, input_output):
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
                  'PRE-CONFIG:VMANAGE: vManage needs to prepare the hard drive and reboot.  ')

            timer_response = wait_timer(device['thread_header'] + 'Waiting for vManage to start reboot.  DO NOT SHUT DOWN VMANAGE.',
                                        device, b'Restarting system', telnet_obj=telnet_obj, interval=5, max_time=1200)
            if timer_response:
                print('\n' + device['thread_header'] + 'PRE-CONFIG:VMANAGE:SUCCESS: Reboot is starting.  '
                                                       'This should not take more than 5-10 minutes. If it does, '
                                                       'stop the vmanage device in EVE-NG and start it again.')
            else:
                print(device['thread_header'] + 'PRE-CONFIG:VMANAGE:FAILURE: vManage reboot is not starting as expected.')

            timer_response = wait_timer('Waiting for vManage to build HDD and reboot.  DO NOT SHUT DOWN VMANAGE.',
                        device, b'System Ready', telnet_obj=telnet_obj, interval=5)
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
                print(device['thread_header'] + 'WRITE_CONFIG: Finished sending commands.  Leaving function.')
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


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Keyboard interupt.  Exiting program.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)


