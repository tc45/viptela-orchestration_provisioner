import requests
import json
from pprint import pprint

base_ip = '172.28.43.174'

baseurl = "https://%s:8443"%(base_ip)

def login():
    authentication_endpoint = "/j_security_check"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    body = {
        "j_username": "admin",
        "j_password": "insight",
    }

    session = requests.session()
    requests.packages.urllib3.disable_warnings()

    url = f"{baseurl}{authentication_endpoint}"
    login_response = session.post(url, data=body, verify=False)

    if b'<html>' in login_response.content:
        print("Login Failed")
        import sys
        sys.exit(0)
    else:
        # print("Login succeeded")
        return session


def set_certificate():
    session = login()

    controller_endpoint = "/dataservice/system/device/controllers"


def post_request(mount_point, payload):
    session = login()
    url = 'https://%s:8443/dataservice/%s'%(base_ip, mount_point)

    payload = json.dumps(payload)
    response = session.post(url=url, data=payload, headers=headers, verify=False)
    data = response.content


def get_devicecontrollers():
    session = login()

    controller_endpoint = "/dataservice/system/device/controllers"
    url = f"{baseurl}{controller_endpoint}"
    print(url)
    response_controller = session.get(url, verify=False)

    devices = response_controller.json()['data']

    for device in devices:
        print(f"Device controller => {device['deviceType']} with IP address {device['deviceIP']}")


def get_vedges():
    session = login()

    vedge_endpoint = "/dataservice/system/device/vedges"
    url = f"{baseurl}{vedge_endpoint}"

    response_controller = session.get(url, verify=False).json()
    vedges = response_controller['data']

    for vedge in vedges:
        print(f"vEdge device => {vedge['deviceModel']} with serialnumber {vedge['serialNumber']}")


def get_csr1000v():
    session = login()

    controller_endpoint = "/dataservice/system/device/vedges?model=vedge-CSR-1000v"
    url = f"{baseurl}{controller_endpoint}"

    response_controller = session.get(url, verify=False).json()
    devices = response_controller['data']

    for device in devices:
        print(f"CSR1000v device => {device['deviceModel']} with serialnumber {device['serialNumber']}")


def get_templates():
    session = login()

    template_endpoint = "/dataservice/template/device"
    url = f"{baseurl}{template_endpoint}"

    response_template = session.get(url, verify=False).json()
    # pprint(response_template)

    templates = response_template['data']

    for template in templates:
        print(f"Template => {template['deviceType']} with id {template['templateId']}")


if __name__ == "__main__":
    response = login()
    print(response)
    response = get_devicecontrollers()
    print(response)
    print(20 * "--" + "vEdge devices" + 20 * "--")
    vedges = get_vedges()
    print(20 * "--" + "CSR1000v devices" + 20 * "--")
    csr1000v = get_csr1000v()
    print(20 * "--" + "Templates" + 20 * "--")
    response = get_templates()