import platform
import sys


def system_info():
    print(f"System: {platform.system()}")
    print(f"Node Name: {platform.node()}")
    print(f"Release: {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Python Version: {sys.version}")


if __name__ == "__main__":
    system_info()
