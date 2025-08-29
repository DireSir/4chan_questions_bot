import socket
import sys
import os

SOCKET_PATH = "/tmp/mybot_console.sock"
if not os.path.exists(SOCKET_PATH):
  print("socket not found:", SOCKET_PATH)
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
      sock.sendall((line + "\n").encode())
      resp = sock.recv(65536)
      if not resp:
        break
      print(resp.decode(), end="")
      if line.lower() in ("quit", "exit"):
        break
  except KeyboardInterrupt:
    pass

if __name__ == "__main__":
  sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  sock.connect(SOCKET_PATH)
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