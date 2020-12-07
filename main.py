from netmiko import ConnectHandler, SSHDetect, NetmikoTimeoutException, NetmikoAuthenticationException

from getpass import getpass


vmanage_console = {
        'device_type': 'generic_termserver_telnet',
        'host': '172.28.43.171',
        'port': '32769',
        'username': 'admin',
        'password': 'insight',
}

logged_in = False

try:
    with ConnectHandler(**vmanage_console) as telnet:
        while not logged_in:
            output = telnet.send_command('\n')
            if output == "vmanage#":
                logged_in = True
                output = telnet.send_command("config")
                print(output)
                telnet.disconnect()
except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
    print(error)

#
#
# vmanage_mgmt =  {
#         'device_type': "autodetect",
#         'host': '172.28.43.174',
#         'username': 'admin',
#         'password': 'insight',
# }
# vsmart_mgmt = {
#         'device_type': "autodetect",
#         'host': '172.28.43.173',
#         'username': 'admin',
#         'password': 'insight',
# }
# vbond_mgmtd = {
#         'device_type': "autodetect",
#         'host': '172.28.43.175',
#         'username': 'admin',
#         'password': 'insight',
# }
#
# devices = [vmanage_mgmt, vsmart_mgmt, vbond_mgmtd]
#
# for device in devices:
#     guesser = SSHDetect(**device)
#     best_match = guesser.autodetect()
#     print('Best match: ')
#     print(best_match)
#     print('Potential matches: ')
#     print(guesser.potential_matches)
#
#     if best_match is not None:
#         device['device_type'] = best_match
#     else:
#         device['device_type'] = 'terminal_server'
#
#     with ConnectHandler(**device) as connection:
#         prompt = connection.find_prompt()
#         print('Prompt is ' + prompt)





