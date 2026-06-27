import hashlib
from pathlib import Path
from PIL import Image


def md5_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.md5()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def average_hash(path: str | Path, size: int = 8) -> str:
    img = Image.open(path).convert('L').resize((size, size))
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ''.join('1' if p > avg else '0' for p in pixels)
    return f"{int(bits, 2):0{size * size // 4}x}"


def hamming_hex(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count('1')
