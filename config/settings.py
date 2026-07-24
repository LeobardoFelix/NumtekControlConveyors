import configparser
import os

DEV_MODE = os.environ.get("NUTRIX_DEV_MODE", "0") == "1"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")

# Defaults applied before reading the file, so every key always resolves.
_DEFAULTS = {
    "ROBOTS": {"ip1": "10.170.83.210", "ip2": "10.170.83.211"},
    "PORT": {"port1": "4840", "port2": "4840"},
    "OPCUA": {"url1": "", "url2": ""},
    "SSH": {
        "user": "numtek",
        "password": "123",
        "program_dir": "/home/numtek/Desktop/COMPARTIDA",
    },
    "BACKUP": {"shared_folder": "/home/johan/Desktop"},
    "ADMIN": {"password": "123"},
    "SIMULATION": {"enabled": "false"},
}


class Settings:

    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self._parser = configparser.ConfigParser()
        self.reload()

    def reload(self):
        self._parser.read_dict(_DEFAULTS)
        if os.path.exists(self.path):
            self._parser.read(self.path)

    def save(self):
        with open(self.path, "w") as f:
            self._parser.write(f)

    @property
    def ip1(self):
        return self._parser.get("ROBOTS", "ip1")

    @property
    def ip2(self):
        return self._parser.get("ROBOTS", "ip2")

    @property
    def port1(self):
        return self._parser.getint("PORT", "port1")

    @property
    def port2(self):
        return self._parser.getint("PORT", "port2")

    def robot_ips(self):
        return self.ip1, self.ip2

    def opcua_urls(self):
        url1 = self._parser.get("OPCUA", "url1") or f"opc.tcp://{self.ip1}:{self.port1}"
        url2 = self._parser.get("OPCUA", "url2") or f"opc.tcp://{self.ip2}:{self.port2}"
        return url1, url2

    def set_robot_ips(self, ip1, ip2):
        self._parser.set("ROBOTS", "ip1", str(ip1))
        self._parser.set("ROBOTS", "ip2", str(ip2))
        self.save()

    def set_opcua_urls(self, url1, url2):
        self._parser.set("OPCUA", "url1", url1)
        self._parser.set("OPCUA", "url2", url2)
        self._parser.set("PORT", "port1", url1.split(":")[2])
        self._parser.set("PORT", "port2", url2.split(":")[2])
        self.save()

    @property
    def ssh_user(self):
        return self._parser.get("SSH", "user")

    @property
    def ssh_password(self):
        return self._parser.get("SSH", "password")

    @property
    def program_dir(self):
        return self._parser.get("SSH", "program_dir")

    @property
    def backup_shared_folder(self):
        return self._parser.get("BACKUP", "shared_folder")

    @property
    def admin_password(self):
        return self._parser.get("ADMIN", "password")

    @property
    def simulation(self):
        return self._parser.getboolean("SIMULATION", "enabled")

    @simulation.setter
    def simulation(self, value: bool):
        self._parser.set("SIMULATION", "enabled", "true" if value else "false")
        self.save()


settings = Settings()
