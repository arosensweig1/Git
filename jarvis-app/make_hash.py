"""Generate a bcrypt hash for a website-login password.

    python make_hash.py 'banking590!!!'

Copy the printed  username:hash  into APP_USERS in your .env.
Never commit .env. Rotate the seeded test credential before real use."""
import sys
import bcrypt

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python make_hash.py '<password>' [username]")
        raise SystemExit(1)
    pw = sys.argv[1].encode()
    user = sys.argv[2] if len(sys.argv) > 2 else "aragpjarvistest1"
    h = bcrypt.hashpw(pw, bcrypt.gensalt()).decode()
    print(f"{user}:{h}")
