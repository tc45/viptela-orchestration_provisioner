from pythonping import ping


def ping_host(ip, count=1):
    response = ping(ip, count)
    if (count - response.packets_lost) > 0:
        return True
