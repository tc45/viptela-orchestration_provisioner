"""
Class with REST Api GET and POST libraries

Example: python rest_api_lib.py vmanage_hostname username password

PARAMETERS:
    vmanage_hostname : Ip address of the vmanage or the dns name of the vmanage
    username : Username to login the vmanage
    password : Password to login the vmanage

Note: All the three arguments are manadatory
"""
import requests
import sys
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from pprint import pprint
import time

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

ca = '''-----BEGIN CERTIFICATE-----
MIIDczCCAlugAwIBAgIJAJV6e0beddnDMA0GCSqGSIb3DQEBCwUAMFAxCzAJBgNV
BAYTAlVTMQswCQYDVQQIDAJBWjEMMAoGA1UEBwwDUEhYMRAwDgYDVQQKDAd0ZXN0
bGFiMRQwEgYDVQQDDAt2bWFuYWdlLmxhYjAeFw0yMDEyMTIxNTIyMDhaFw0yNjA2
MDQxNTIyMDhaMFAxCzAJBgNVBAYTAlVTMQswCQYDVQQIDAJBWjEMMAoGA1UEBwwD
UEhYMRAwDgYDVQQKDAd0ZXN0bGFiMRQwEgYDVQQDDAt2bWFuYWdlLmxhYjCCASIw
DQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALrTFkOpa4Uf+ZOA0Lrjga3ce85S
w5Y/cVKjZBvRflYUdDEmaoFYRAkPVCgjvHS3Db+plbdd14jKmu3vfKuHGtJHbXmb
XWqhhQhQz+UTcS8S+bHsGAGf15JRcRHAfLIwUQaV5uUaOTKm72uTFwxj/Kqg1mVb
O1KYKMCN7Cvrbd4qPc68rvXS4+yWCqt5+OaGbm71VSSoayg4/hBFU42x9bylFcfj
LopeI6X6XoiepZgXaLTiHx3P7Z88p8wD2noLq/XOMGxYZzLiyzYC4bqE6mNjZv+E
2aqQAmUUhRdFyP3cSQB59JuLghQ3tlVQRbuubgbYqEjXT8ZydHDTvPedYKECAwEA
AaNQME4wHQYDVR0OBBYEFCzQUpLv8249djO5uKrJO9tGztLFMB8GA1UdIwQYMBaA
FCzQUpLv8249djO5uKrJO9tGztLFMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBAFwLmhtpPVAAyxbWaa8laB4a29+jFMWC5xxPC4IVyCdsI6KPbCV2azMU
Oiq3bEkzT4ETS5s1TwUck67iiCCcHt8si2WAcpLABb5n854geul4pAg+wyc4qo9C
wZFvvzeLMtdaJRw2HMiKYqP/iNuRU305fMynWTjznsDgaSeZrsPMZrKIV39JmNLB
7l+x0JSa2PVuju4GlELGZ1f0rIoXO3TFQyIXinQxp1WwRJ/7SPyQ8kfKzpzdxoVy
vOEP9eTWhsDDLIM7N+0UlgyvB1YX9o0XsHklaE0RFk79kzEELIMeDFjT5sxENloY
htGzCFDcVK3wwZcralx8ePE/kDLOQy0=
-----END CERTIFICATE-----'''


class rest_api_lib:
    def __init__(self, vmanage_ip, username, password):
        self.vmanage_ip = vmanage_ip
        self.session = {}
        self.login(self.vmanage_ip, username, password)

    def login(self, vmanage_ip, username, password):
        """Login to vmanage"""
        base_url_str = 'https://%s' % vmanage_ip

        login_action = '/j_security_check'

        # Format data for loginForm
        login_data = {'j_username': username, 'j_password': password}

        # Url for posting login data
        login_url = base_url_str + login_action

        sess = requests.session()

        # If the vmanage has a certificate signed by a trusted authority change verify to True
        login_response = sess.post(url=login_url, data=login_data, verify=False)

        if b'<html>' in login_response.content:
            print("Login Failed")
            sys.exit(0)

        # update token to session headers

        token_url = 'https://%s/dataservice/client/token?json=true' % vmanage_ip
        login_token = sess.get(url=token_url, verify=False)

        if login_token.status_code == 200:
            if b'<html>' in login_token.content:
                print("Login Token Failed")
                exit(0)

            sess.headers['X-XSRF-TOKEN'] = json.loads(login_token.content.decode())['token']

        self.session[vmanage_ip] = sess

    def get_request(self, mount_point):
        """GET request"""
        url = "https://%s:8443/dataservice/%s" % (self.vmanage_ip, mount_point)
        print('Getting info at: ' + url)
        response = self.session[self.vmanage_ip].get(url, verify=False)
        return response

    def post_request(self, mount_point, payload, files=None, headers={'Content-Type': 'application/json'}):
        """POST request"""
        url = "https://%s:8443/dataservice/%s" % (self.vmanage_ip, mount_point)
        print('Pushing payload to: ' + url)
        payload = json.dumps(payload)
        response = self.session[self.vmanage_ip].post(url, data=payload, headers=headers, files=files, verify=False)
        return response

    def put_request(self, mount_point, payload, files=None, headers={'Content-Type': 'application/json'}):
        """POST request"""
        url = "https://%s:8443/dataservice/%s" % (self.vmanage_ip, mount_point)
        print('Putting payload to: ' + url)
        payload = json.dumps(payload)
        response = self.session[self.vmanage_ip].put(url, data=payload, headers=headers, files=files, verify=False)
        return response


def run_api(api_obj, mount_point, payload=None, method='get', files=None):
    if method == 'get':
        if files is not None:
            response = api_obj.get_request(mount_point, files=files)
        else:
            response = api_obj.get_request(mount_point)
    elif method == 'post':
        if files is not None:
            response = api_obj.post_request(mount_point, payload, files=files)
        else:
            response = api_obj.post_request(mount_point, payload)
    elif method == 'put':
        if files is not None:
            response = api_obj.put_request(mount_point, payload, files=files)
        else:
            response = api_obj.put_request(mount_point, payload)

    print(str(response.status_code) + ' ' + response.reason)
    if response.status_code != 200:
        print(response.content.decode())
    time.sleep(2)


def main(args):
    if not len(args) == 3:
        print(__doc__)
        return
    vmanage_ip, username, password = args[0], args[1], args[2]
    obj = rest_api_lib(vmanage_ip, username, password)
    # Example request to get devices from the vmanage "url=https://vmanage.viptela.com/dataservice/device"
    run_api(obj, 'system/device/vedges')
    # Example request to get devices from the vmanage "url=https://vmanage.viptela.com/dataservice/device"
    payload = {"action": "rediscover", "devices": [{"deviceIP": "172.16.248.105"}, {"deviceIP": "172.16.248.106"}]}
    run_api(obj, 'device/action/rediscover', payload=payload, method='post')    # Example request to get devices from the vmanage "url=https://vmanage.viptela.com/dataservice/device"
    payload = {
        'domain-id': '1',
        'org': 'TEST',
        'password': 'insight',
    }
    run_api(obj, 'settings/configuration/organization', payload=payload, method='put')
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'domainIp': '2.2.2.2',
        'port': 12346
    }
    run_api(obj, 'settings/configuration/device', payload, method='put')
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'certificateSigning': 'enterprise'
    }
    run_api(obj, 'settings/configuration/certificate', payload, method='post')
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'enterpriseRootCA': ca
    }
    run_api(obj, 'settings/configuration/certificate/enterpriserootca', payload, method='put')
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {'data': {'validity': 'valid', 'upload': 'true'}}
    files = {'file': ('serialFile (1).viptela',  open('C:/Users/Tony Curtis/Desktop/serialFile (1).viptela', 'rb'))}
    response = obj.post_request('system/device/fileupload', payload, files=files, headers={'Content-Type': 'multipart/form-data'})

    # response = obj.get_request('system/device/vedges')
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {"action": "rediscover", "devices": [{"deviceIP": "172.16.248.105"}, {"deviceIP": "172.16.248.106"}]}
    # response = obj.post_request('device/action/rediscover', payload)
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)
    # # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {
    #     'domain-id': '1',
    #     'org': 'TEST',
    #     'password': 'insight',
    # }
    # response = obj.put_request('settings/configuration/organization', payload)
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)
    # # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {
    #     'domainIp': '2.2.2.2',
    #     'port': 12346
    # }
    # response = obj.put_request('settings/configuration/device', payload)
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {
    #     'certificateSigning': 'enterprise'
    # }
    # response = obj.post_request('settings/configuration/certificate', payload)
    # print(str(response.status_code) + ' ' + response.reason)
    # time.sleep(2)
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {
    #     'enterpriseRootCA': ca
    # }
    # response = obj.put_request('settings/configuration/certificate/enterpriserootca', payload)
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)
    # Example request to make a Post call to the vmanage "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    # payload = {'data': {'validity': 'valid', 'upload': 'true'}}
    # files = {'file': ('serialFile (1).viptela',  open('C:/Users/Tony Curtis/Desktop/serialFile (1).viptela', 'rb'))}
    #
    # # files = [
    # #     ('', ('serialFile (1).viptela', open('C:/Users/Tony Curtis/Desktop/serialFile (1).viptela', 'rb'),
    # #           'application/octet-stream'))
    # # ]
    # response = obj.post_request('system/device/fileupload', payload, files=files, headers={'Content-Type': 'multipart/form-data'})
    # print(str(response.status_code) + ' ' + response.reason)
    # if response.status_code != 200:
    #     print(response.content.decode())
    # time.sleep(2)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))