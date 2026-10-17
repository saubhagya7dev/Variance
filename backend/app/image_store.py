import hashlib
import http.client
import ipaddress
import socket
import ssl
import time
import warnings
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 20_000_000


def public_addresses(host: str) -> list[str]:
    addresses = list(
        dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
    )
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("Only public internet image addresses are allowed.")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Connect to the checked numeric address, preserving TLS SNI/certificate verification.
        raw = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def download_image(url: str) -> bytes:
    deadline = time.monotonic() + 30
    for _ in range(4):
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
            or len(url) > 4096
        ):
            raise ValueError("Reference downloads require a public HTTPS URL on port 443.")
        host = parts.hostname.encode("idna").decode("ascii")
        addresses = public_addresses(host)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Image download timed out.")
        connection = PinnedHTTPSConnection(host, addresses[0], min(remaining, 10))
        try:
            target = (parts.path or "/") + ("?" + parts.query if parts.query else "")
            connection.request(
                "GET",
                target,
                headers={
                    "User-Agent": "VarianceLocalStudio/0.3",
                    "Accept": "image/*",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Image redirect is missing its destination.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f"Image server returned HTTP {response.status}.")
            if response.getheader("Content-Type", "").split(";")[0].lower() not in (
                "image/png",
                "image/jpeg",
                "image/webp",
            ):
                raise ValueError("Only PNG, JPEG, and WebP reference images are supported.")
            length = response.getheader("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("Image exceeds the 8 MB download limit.")
            chunks, size = [], 0
            while True:
                if time.monotonic() >= deadline:
                    raise ValueError("Image download timed out.")
                chunk = response.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Image exceeds the 8 MB download limit.")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            connection.close()
    raise ValueError("Too many image redirects.")


def normalize_image(raw: bytes) -> tuple[bytes, int, int]:
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Choose a PNG, JPEG, or WebP image no larger than 8 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if (
                    source.format not in ("PNG", "JPEG", "WEBP")
                    or source.width * source.height > MAX_PIXELS
                ):
                    raise ValueError("Use a PNG, JPEG, or WebP image with at most 20 megapixels.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Animated images are not supported; choose one still frame.")
                source.load()
                normalized = ImageOps.exif_transpose(source).convert("RGB")
                normalized.thumbnail((4096, 4096))
                # New pixel-only image strips metadata, profiles and embedded payloads.
                clean = Image.frombytes("RGB", normalized.size, normalized.tobytes())
                output = BytesIO()
                clean.save(output, format="PNG")
                return output.getvalue(), clean.width, clean.height
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError("This file is not a valid supported image.") from exc


def store_image(root: Path, raw: bytes) -> tuple[str, int, int]:
    content, width, height = normalize_image(raw)
    digest = hashlib.sha256(content).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{digest}.png"
    if not destination.exists():
        temporary = root / f"{uuid4().hex}.tmp"
        try:
            temporary.write_bytes(content)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return digest, width, height
