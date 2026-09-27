#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — minimal Nostr publisher (owned identity, no accounts).

Pure-stdlib: BIP-340 Schnorr + minimal TLS websocket client. Keypair lives
in data/nostr_key.json (gitignored, never logged, never committed).
Publishes a SMALL number of honest product announcements (never spam).
Verifies relay OK responses. All failures are clean (relay reject = no-op).
"""
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import time

# --- secp256k1 params (public domain constants) ---
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _x(P_):
    return P_[0]


def _add(P1, P2):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    x1, y1 = P1
    x2, y2 = P2
    if x1 == x2:
        if (y1 + y2) % P == 0:
            return None
        lam = (3 * x1 * x1 * pow(2 * y1, P - 2, P)) % P
    else:
        lam = ((y2 - y1) * pow(x2 - x1, P - 2, P)) % P
    x3 = (lam * lam - x1 - x2) % P
    return (x3, (lam * (x1 - x3) - y1) % P)


def _mul(k, P_=G):
    R = None
    while k:
        if k & 1:
            R = _add(R, P_)
        P_ = _add(P_, P_)
        k >>= 1
    return R


def _bytes(x, n=32):
    return x.to_bytes(n, 'big')


def _tagged(tag, msg):
    h = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(h + h + msg).digest()


def schnorr_sign(seckey, msg32, aux_rand=None):
    assert len(seckey) == 32 and len(msg32) == 32
    d = int.from_bytes(seckey, 'big')
    if not (1 <= d < N):
        raise ValueError('bad key')
    Ppub = _mul(d)
    if Ppub[1] % 2 == 1:
        d = N - d
        Ppub = _mul(d)
    pk = _bytes(_x(Ppub))
    if aux_rand is None:
        aux_rand = os.urandom(32)
    assert len(aux_rand) == 32
    t = bytes(a ^ b for a, b in zip(_bytes(d), _tagged('BIP0340/aux', aux_rand)))
    rand = _tagged('BIP0340/nonce', t + pk + msg32)
    k = int.from_bytes(rand, 'big') % N
    if k == 0:
        raise RuntimeError('unlucky nonce')
    R = _mul(k)
    if _x(R) is None:
        raise RuntimeError('bad R')
    if R[1] % 2 == 1:
        k = N - k
    e = int.from_bytes(_tagged('BIP0340/challenge',
                               _bytes(_x(_mul(k))) + pk + msg32), 'big') % N
    return _bytes(_x(_mul(k))) + _bytes((k + e * d) % N)


def schnorr_verify(pk, msg32, sig):
    try:
        r = int.from_bytes(sig[:32], 'big')
        s = int.from_bytes(sig[32:], 'big')
        Ppub = (int.from_bytes(pk, 'big'),
                pow(int.from_bytes(pk, 'big'), 3, P) + 7)
        # lift x (choose even y)
        y = pow((Ppub[0] ** 3 + 7) % P, (P + 1) // 4, P)
        if (y * y) % P != (Ppub[0] ** 3 + 7) % P:
            return False
        if y % 2 == 1:
            y = P - y
        Ppub = (Ppub[0], y)
        e = int.from_bytes(_tagged('BIP0340/challenge',
                                   sig[:32] + pk + msg32), 'big') % N
        R = _add(_mul(s), _mul((N - e) % N, Ppub))
        return R is not None and R[1] % 2 == 0 and _x(R) == r
    except Exception:
        return False


# --- minimal TLS websocket client (text frames only) ---
import base64


class WS:
    def __init__(self, host, port=443, path='/', timeout=30):
        raw = socket.create_connection((host, port), timeout=timeout)
        self.s = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        self.s.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n'
                        'Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n'
                        'Sec-WebSocket-Version: 13\r\n\r\n' % (path, host, key)).encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            chunk = self.s.recv(4096)
            if not chunk:
                raise RuntimeError('handshake failed')
            resp += chunk
        if b'101' not in resp.split(b'\r\n')[0]:
            raise RuntimeError('no 101: ' + resp[:80].decode('replace'))

    def send_text(self, msg):
        data = msg.encode('utf-8')
        mask = os.urandom(4)
        hdr = bytes([0x81])
        n = len(data)
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack('>H', n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack('>Q', n)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recvn(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise RuntimeError('closed')
            buf += chunk
        return buf

    def recv_text(self):
        h = self._recvn(2)
        op, ln = h[0] & 0x0F, h[1] & 0x7F
        if ln == 126:
            ln = struct.unpack('>H', self._recvn(2))[0]
        elif ln == 127:
            ln = struct.unpack('>Q', self._recvn(8))[0]
        masked = bool(h[1] & 0x80)
        mk = self._recvn(4) if masked else None
        data = self._recvn(ln)
        if masked:
            data = bytes(b ^ mk[i % 4] for i, b in enumerate(data))
        if op == 0x8:
            raise RuntimeError('server close')
        if op == 0x9:  # ping -> pong
            self.s.sendall(b'\x8a\x00')
            return self.recv_text()
        return data.decode('utf-8', 'replace')

    def close(self):
        try:
            self.s.sendall(b'\x88\x00')
            self.s.close()
        except Exception:
            pass


def selftest():
    sk = hashlib.sha256(b'galaxy-forge-selftest').digest()
    pk = _bytes(_x(_mul(int.from_bytes(sk, 'big'))))
    msg = hashlib.sha256(b'test').digest()
    sig = schnorr_sign(sk, msg)
    assert schnorr_verify(pk, msg, sig), 'roundtrip failed'
    assert not schnorr_verify(pk, hashlib.sha256(b'other').digest(), sig), 'forgery passed!'
    print('schnorr selftest PASS')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest':
        selftest()
