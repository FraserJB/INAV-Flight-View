import subprocess
import time
import os

start = time.time()
script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
p = subprocess.Popen(["python", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
print("Starting main.py...")

for line in p.stdout:
    print(line, end='')
    if "SPLASH_SHOWN" in line:
        elapsed = time.time() - start
        print(f"\nTotal elapsed time from process start to splash: {elapsed:.4f} seconds")
        break

p.terminate()
