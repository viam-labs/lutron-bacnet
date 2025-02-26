import socket
import random


def get_available_port(start_range=47809, end_range=65535):
    """
    Find an available UDP port within the specified range.

    Args:
        start_range: Lower bound of port range (default: 47809)
        end_range: Upper bound of port range (default: 65535)

    Returns:
        An available port number
    """
    # Create a list of potential ports in random order
    potential_ports = list(range(start_range, end_range))
    random.shuffle(potential_ports)

    # Try each port until we find an available one
    for port in potential_ports:
        try:
            # Create a UDP socket and try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("0.0.0.0", port))
            sock.close()
            return port
        except OSError:
            # Port is in use, try next one
            continue

    raise RuntimeError("No available ports found in the specified range")
