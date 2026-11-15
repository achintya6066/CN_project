#!/usr/bin/env python3
"""UDP echo responder used by the diagnostic client."""
import argparse
import socket

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=9999)
    a = p.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((a.host, a.port))
    print(f"UDP echo server listening on {a.host}:{a.port}")
    try:
        while True:
            data, addr = sock.recvfrom(2048)
            sock.sendto(data, addr)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
