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


class vmanage_lib:
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
        response = None
        response = self.session[self.vmanage_ip].get(url, verify=False)
        return response

    def post_request(self, mount_point, payload, files=None, headers=''):
        """POST request"""
        url = "https://%s:8443/dataservice/%s" % (self.vmanage_ip, mount_point)
        print('Pushing payload to: ' + url)
        response = None
        if headers is not None:
            if headers['Content-Type'] == 'application/json':
                payload = json.dumps(payload)
        response = self.session[self.vmanage_ip].post(url, data=payload, headers=headers, files=files, verify=False)
            # print('ERROR: Value error supplied for this job.  Message: ' + error.args[0])
        return response

    def put_request(self, mount_point, payload, files=None, headers=''):
        """PUT request"""
        url = "https://%s:8443/dataservice/%s" % (self.vmanage_ip, mount_point)
        print('Putting payload to: ' + url)
        response = None

        payload = json.dumps(payload)
        response = self.session[self.vmanage_ip].put(url, data=payload, headers=headers, files=files, verify=False)
        return response

    def run_api(self, mount_point, payload=None, method='get', files=None, headers=''):
        response = None
        if headers is None:
            pass
        elif headers != '':
            for key, value in headers.items():
                headers[key] = value
        else:
            headers = {'Content-Type': 'application/json'}
        if method == 'get':
            if files is not None:
                response = self.get_request(mount_point, files=files)
            else:
                response = self.get_request(mount_point)
        elif method == 'post':
            if files is not None:
                response = self.post_request(mount_point, payload, files=files, headers=headers)
            else:
                response = self.post_request(mount_point, payload, headers=headers)
        elif method == 'put':
            if files is not None:
                response = self.put_request(mount_point, payload, files=files, headers=headers)
            else:
                response = self.put_request(mount_point, payload, headers=headers)
        print(str(response.status_code) + ' ' + response.reason)
        if response.status_code != 200:
            print(response.content.decode())
        if response is None:
            return False
        else:
            return response


def main(args):
    if not len(args) == 3:
        print(__doc__)
        return
    vmanage_ip, username, password = args[0], args[1], args[2]
    obj = vmanage_lib(vmanage_ip, username, password)
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
    # Example request to make a Post call to the vmanage
    # "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'domainIp': '2.2.2.2',
        'port': 12346
    }
    run_api(obj, 'settings/configuration/device', payload, method='put')
    # Example request to make a Post call to the vmanage
    # "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'certificateSigning': 'enterprise'
    }
    run_api(obj, 'settings/configuration/certificate', payload, method='post')
    # Example request to make a Post call to the vmanage
    # "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"
    payload = {
        'enterpriseRootCA': ca
    }
    run_api(obj, 'settings/configuration/certificate/enterpriserootca', payload, method='put')
    # Example request to make a Post call to the vmanage
    # "url=https://vmanage.viptela.com/dataservice/device/action/rediscover"


    files = [
        ("file", ("DEFAULT - 155893.viptela", open("C:/Users/Tony Curtis/Desktop/DEFAULT - 155893.viptela", "rb"),
                  "application/octet-stream"))
    ]
    payload = [{"validity": "valid", "upload": True}]
    response = run_api(obj, 'system/device/fileupload', payload, files=files, method='post',
            headers=None)

    print(response.text)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))