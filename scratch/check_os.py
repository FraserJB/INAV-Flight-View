import os
import sys

def check():
    try:
        print(f"OS is: {os}")
    except NameError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
