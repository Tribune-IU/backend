import sys
from cryptography.fernet import Fernet
from pathlib import Path

# Configuration
KEY_FILE = Path(".vault.key")
ENV_FILE = Path(".env")
ENC_FILE = Path(".env.enc")


def get_key():
    if not KEY_FILE.exists():
        print(f"[INFO] Generating new key at {KEY_FILE}")
        print("[WARNING] ADD .vault.key TO .GITIGNORE IMMEDIATELY")
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)

    with open(KEY_FILE, "rb") as f:
        return f.read()


def lock():
    if not ENV_FILE.exists():
        print(f"[ERROR] {ENV_FILE} not found.")
        return

    fernet = Fernet(get_key())
    with open(ENV_FILE, "rb") as f:
        data = f.read()

    with open(ENC_FILE, "wb") as f:
        f.write(fernet.encrypt(data))
    print(f"[SUCCESS] Encrypted {ENV_FILE} to {ENC_FILE}")


def unlock():
    if not ENC_FILE.exists():
        print(f"[ERROR] {ENC_FILE} not found.")
        return

    fernet = Fernet(get_key())
    with open(ENC_FILE, "rb") as f:
        data = f.read()

    with open(ENV_FILE, "wb") as f:
        f.write(fernet.decrypt(data))
    print(f"[SUCCESS] Decrypted {ENC_FILE} to {ENV_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vault.py [lock|unlock]")
    elif sys.argv[1] == "lock":
        lock()
    elif sys.argv[1] == "unlock":
        unlock()
