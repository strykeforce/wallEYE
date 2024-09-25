import socket
import logging
import os

logger = logging.getLogger(__name__)

ETHERNET = "end1" # 22.04 eth0


# Set static IP and write it into system files
def set_ip(ip: str, interface: str = ETHERNET):
    logger.info("Attempting to set static IP")

    if not ip:
        logger.warning("IP is None")
        return

    # Set IP
    # os.system(
    #     'nmcli --terse connection show | cut -d : -f 1 | while read name; do echo nmcli connection delete "$name"; done'
    # )
    # # os.system("ifconfig eth0 down")
    os.system("ifconfig eth0 up")
    if not os.system(f"/usr/sbin/ifconfig {interface} {ip} netmask 255.255.255.0") and get_current_ip() == ip:
        logger.info(f"Static IP set: {ip} =? {get_current_ip()}")
    else:
        logger.error(f"Failed to set static ip: {ip}, actually at {get_current_ip()}")
    os.system("/usr/sbin/ifconfig eth0 up")


    logger.info(f"Static IP set: {ip} =? {get_current_ip()}")


def get_current_ip(interface: str = ETHERNET):
    try:
        return (
            os.popen(f'ip addr show {interface} | grep "\<inet\>"')
            .read()
            .split()[1]
            .split("/")[0]
            .strip()
        )
    except IndexError:
        logger.error("Could not get current IP - Returning None")
        return None
