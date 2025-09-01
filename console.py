import socket
import sys
import os
from functions import config

socket_path = config["socket_path"]
if not os.path.exists(socket_path):
  print("socket not found:", socket_path)
  sys.exit(1)

def interact(sock):
  try:
    data = sock.recv(4096)
    if data:
      print(data.decode(), end="")
    while True:
      try:
        line = input().strip()
      except EOFError:
        break
      if not line:
        continue
      try:
        sock.sendall((line + "\n").encode())
        resp = sock.recv(65536)
        print(resp.decode(), end="")
        if line.lower() in ("quit", "exit", "stop"):
          break
      except BrokenPipeError:
        print(f"{BrokenPipeError}, The bot is not running.")
  except KeyboardInterrupt:
    pass

if __name__ == "__main__":
  sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  try:
    sock.connect(socket_path)
    try:
      if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:]) + "\n"
        sock.sendall(cmd.encode())
        out = sock.recv(65536)
        print(out.decode(), end="")
      else:
        interact(sock)
    finally:
      sock.close()
  except ConnectionRefusedError:
    print("The bot is not running.")