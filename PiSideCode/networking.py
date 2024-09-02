import socket
import logging
import struct
import fcntl

logger = logging.getLogger(__name__)


SIOCSIFADDR = 0x8916
SIOCGIFADDR = 0x8915
SIOCSIFNETMASK = 0x891C
networking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd = networking_socket.fileno()


# Set static IP and write it into system files
def set_ip(ip: str, interface: str = "eth0"):
    logger.info("Attempting to set static IP")

    if not ip:
        logger.warning("IP is None")
        return

    # https://stackoverflow.com/questions/20420937/how-to-assign-ip-address-to-interface-in-python
    bin_ip = socket.inet_aton(ip)
    ifreq = struct.pack(
        b"16sH2s4s8s",
        interface.encode("utf-8"),
        socket.AF_INET,
        b"\x00" * 2,
        bin_ip,
        b"\x00" * 8,
    )
    # https://stackoverflow.com/questions/70310413/python-fcntl-ioctl-errno-1-operation-not-permitted
    try:
        fcntl.ioctl(networking_socket, SIOCSIFADDR, ifreq)
    except Exception as e:
        logger.error(f"Failed to set IP address: {e}")

    logger.info(f"Static IP set: {ip} =? {get_current_ip()}")


def get_current_ip(interface: str = "eth0"):
    # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/9267833#9267833
    ifreq = struct.pack(
        b"16sH14s", interface.encode("utf-8"), socket.AF_INET, b"\x00" * 14
    )
    try:
        res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
    except Exception as e:
        logger.error(f"Could not get current IP - {e} - Returning None")
        return None

    ip = struct.unpack("16sH2x4s8x", res)[2]
    return socket.inet_ntoa(ip)
