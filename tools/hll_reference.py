#!/usr/bin/env python3
"""The HyperLogLog estimates tests/skaccuracy_tests.nv asserts, from a
second implementation.

This is Ertl's algorithm 6 ("New cardinality estimation algorithms for
HyperLogLog sketches", 2017) written from the paper in Python, fed the
same seeded stream the suite feeds `skhll`: the items are the strings
`"<seed>:<i>"`, hashed with 64-bit FNV-1a and then the SplitMix64
finaliser.  It prints one line per stream, the precision, the seed,
the item count and the estimate, which the suite carries as constants.

Run:  python3 tools/hll_reference.py
"""
import math

M64 = (1 << 64) - 1


def fnv1a(data):
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & M64
    return h


def mix(z):
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9 & M64
    z = (z ^ (z >> 27)) * 0x94d049bb133111eb & M64
    return z ^ (z >> 31)


def item_hash(seed, i):
    return mix(fnv1a(("%d:%d" % (seed, i)).encode()))


def sigma(x):
    if x == 1.0:
        return math.inf
    y, z = 1.0, x
    while True:
        x *= x
        z_old = z
        z += x * y
        y += y
        if z == z_old:
            return z


def tau(x):
    if x == 0.0 or x == 1.0:
        return 0.0
    y, z = 1.0, 1.0 - x
    while True:
        x = math.sqrt(x)
        z_old = z
        y *= 0.5
        z -= (1 - x) ** 2 * y
        if z == z_old:
            return z / 3


def estimate(p, hashes):
    m, q = 1 << p, 64 - p
    regs = [0] * m
    for h in hashes:
        idx = h >> q
        rest = (h << p) & M64
        r = q + 1 if rest == 0 else 64 - rest.bit_length() + 1
        regs[idx] = max(regs[idx], r)
    c = [0] * (q + 2)
    for r in regs:
        c[r] += 1
    if c[0] == m:
        return 0
    z = m * tau(1 - c[q + 1] / m)
    for k in range(q, 0, -1):
        z = 0.5 * (z + c[k])
    z += m * sigma(c[0] / m)
    return round(m * m / (2 * math.log(2)) / z)


STREAMS = [(12, 1, 10), (12, 2, 100), (12, 3, 1000), (12, 4, 10000),
           (12, 5, 30000), (10, 6, 5000), (14, 7, 20000), (4, 8, 500)]

if __name__ == "__main__":
    for p, seed, n in STREAMS:
        e = estimate(p, (item_hash(seed, i) for i in range(n)))
        print(p, seed, n, e, "%.4f" % ((e - n) / n))
