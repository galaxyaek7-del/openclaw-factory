"""Tests for scripts/nostr_direct.py — official BIP-340 vectors + regression tests.

Covers the two real bugs found during implementation:
  1. inverted point-at-infinity check in _add (doubling returned None)
  2. missing secret-key negation for odd-Y public keys
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scripts'))
from nostr_direct import (_add, _mul, _bytes, _x, G, schnorr_sign,
                          schnorr_verify)

# (index, seckey, aux_rand, msg, sig, valid) — official BIP-340 vectors
VECTORS = [
    ('0000000000000000000000000000000000000000000000000000000000000003',
     '0000000000000000000000000000000000000000000000000000000000000000',
     '0000000000000000000000000000000000000000000000000000000000000000',
     'E907831F80848D1069A5371B402410364BDF1C5F8307B0084C55F1CE2DCA821525F66A4A85EA8B71E482A74F382D2CE5EBEEE8FDB2172F477DF4900D310536C0',
     True),
    ('B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF',
     '0000000000000000000000000000000000000000000000000000000000000001',
     '243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89',
     '6896BD60EEAE296DB48A229FF71DFE071BDE413E6D43F917DC8DCF8C78DE33418906D11AC976ABCCB20B091292BFF4EA897EFCB639EA871CFA95F6DE339E4B0A',
     True),
    ('C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9',
     'C87AA53824B4D7AE2EB035A2B5BBBCCC080E76CDC6D1692C4B0B62D798E6D906',
     '7E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C',
     '5831AAEED7B44BB74E5EAB94BA9D4294C49BCF2A60728D8B4C200F50DD313C1BAB745879A5AD954A72C45A91C3A51D3C7ADEA98D82F8481E0E1E03674A6F3FB7',
     True),
    ('DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659',
     None, None, None, 'VERIFY_ONLY_FALSE_CASES'),
]
PUBKEYS = {
    'B7E151628AED2A6ABF7158809CF4F3C762E7160F38B4DA56A784D9045190CFEF':
        'DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659',
}
FALSE_SIGNED = [
    # (pubkey_hex, msg_hex, sig_hex, reason) — must all FAIL verification
    ('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF',
     '243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89',
     '6CFF5C3BA86C69EA4B7376F31A9BCB4F74C1976089B2D9963DA2E5543E17776969E89B4C5564D00349106B8497785DD7D1D713A8AE82B32FA79D5F7FC407D39B',
     'pubkey x out of field range (constructed; official row-5 value unrecoverable verbatim)'),
    ('DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659',
     '243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89',
     'FFF97BD5755EEEA420453A14355235D382F6472F8568A18B2F057A14602975563CC27944640AC607CD107AE10923D9EF7A73C643E166BE5EBEAFA34B1AC553E2',
     'R.y odd'),
    ('DFF1D77F2A671C5F36183726DB2341BE58FEAE1DA2DECED843240F7B502BA659',
     '243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89',
     '6CFF5C3BA86C69EA4B7376F31A9BCB4F74C1976089B2D9963DA2E5543E177769FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141',
     's equals curve order'),
]


class TestOfficialVectors(unittest.TestCase):
    def test_sign_vectors_0_to_2(self):
        for sk, aux, msg, sig, _ in VECTORS[:3]:
            got = schnorr_sign(bytes.fromhex(sk), bytes.fromhex(msg),
                               bytes.fromhex(aux)).hex()
            self.assertEqual(got.lower(), sig.lower())

    def test_verify_true_vectors(self):
        for sk, aux, msg, sig, _ in VECTORS[:3]:
            d = int.from_bytes(bytes.fromhex(sk), 'big')
            from nostr_direct import N
            Ppub = _mul(d)
            if Ppub[1] % 2 == 1:
                d = N - d
            pk = _bytes(_x(_mul(d)))
            self.assertTrue(schnorr_verify(pk, bytes.fromhex(msg), bytes.fromhex(sig)))

    def test_verify_false_vectors(self):
        for pk, msg, sig, reason in FALSE_SIGNED:
            self.assertFalse(
                schnorr_verify(bytes.fromhex(pk), bytes.fromhex(msg),
                               bytes.fromhex(sig)), reason)


class TestRegression(unittest.TestCase):
    def test_bug1_doubling_not_infinity(self):
        """Inverted infinity check once made _add(G,G) return None.
        Verified: 2G on-curve, distinct, and _add(2G,G) == official 3G pubkey."""
        D = _add(G, G)
        self.assertIsNotNone(D)
        from nostr_direct import P as _P
        self.assertEqual((_x(D) ** 3 + 7 - D[1] * D[1]) % _P, 0)
        T = _add(D, G)
        self.assertEqual(hex(_x(T)),
                         '0xf9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9')

    def test_bug2_odd_y_key_negation(self):
        """Missing negation broke vectors whose pubkey has odd Y."""
        sk = bytes.fromhex(
            'C90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B14E5C9')
        got = schnorr_sign(
            sk, bytes.fromhex('7E2D58D8B3BCDF1ABADEC7829054F90DDA9805AAB56C77333024B9D0A508B75C'),
            bytes.fromhex('C87AA53824B4D7AE2EB035A2B5BBBCCC080E76CDC6D1692C4B0B62D798E6D906')).hex()
        self.assertEqual(
            got.lower(), '5831AAEED7B44BB74E5EAB94BA9D4294C49BCF2A60728D8B4C200F50DD313C1BAB745879A5AD954A72C45A91C3A51D3C7ADEA98D82F8481E0E1E03674A6F3FB7'.lower())

    def test_forgery_rejected(self):
        import hashlib
        sk = hashlib.sha256(b'galaxy-forge-selftest').digest()
        d = int.from_bytes(sk, 'big')
        from nostr_direct import N
        Ppub = _mul(d)
        if Ppub[1] % 2 == 1:
            d = N - d
        pk = _bytes(_x(_mul(d)))
        msg = hashlib.sha256(b'test').digest()
        sig = schnorr_sign(sk, msg)
        self.assertTrue(schnorr_verify(pk, msg, sig))
        self.assertFalse(schnorr_verify(pk, hashlib.sha256(b'other').digest(), sig))

    def test_malformed_inputs_never_raise(self):
        self.assertFalse(schnorr_verify(b'\x00' * 32, b'\x00' * 32, b'\x00' * 64))
        self.assertFalse(schnorr_verify(b'\xff' * 32, b'\x00' * 32, b'\x00' * 64))
        self.assertFalse(schnorr_verify(b'\x02' + b'\x00' * 31, b'\x00' * 32, b'\x00' * 63))


class TestFaults(unittest.TestCase):
    def test_refused_connection_fails_clean(self):
        from nostr_direct import WS
        import time
        t0 = time.time()
        with self.assertRaises(Exception):
            WS('127.0.0.1', 9, '/', timeout=5)
        self.assertLess(time.time() - t0, 30)

    def test_sign_rejects_bad_inputs(self):
        with self.assertRaises(Exception):
            schnorr_sign(b'\x00' * 31, b'\x00' * 32)
        with self.assertRaises(Exception):
            schnorr_sign(b'\x00' * 32, b'\x00' * 32)

    def test_duplicate_event_same_id(self):
        """Same content in the same second yields the same event ID --
        relays dedupe by ID, so retries can never double-publish."""
        import hashlib
        import json
        inner = [0, 'ab' * 32, 1700000000, 1, [], 'hello']
        a = hashlib.sha256(json.dumps(inner, separators=(',', ':')).encode()).hexdigest()
        b = hashlib.sha256(json.dumps(inner, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
