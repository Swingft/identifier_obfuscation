import hashlib
import os

def get_short_hash(type):
    # 난수 기반 시드 (매번 다른 값)
    length=6
    random_bytes = os.urandom(16)
    hash_val = hashlib.sha256(random_bytes).hexdigest()
    if type in ["variable", "case"]:
        return f"swingft_{hash_val[:length]}"
    return f"{type}_{hash_val[:length]}"
