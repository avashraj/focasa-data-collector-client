import platform


def get_os() -> str:
    return platform.system()


def get_device_name() -> str:
    return platform.node()
