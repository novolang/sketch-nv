# Changelog

All notable changes to sketch-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## [0.0.1] — 2026-09-17

**The interface, published before anyone implements it.** Every public
type and function carries its full signature, its effect row and its
doc comment; every body is `todo()`; the release is recorded
`implemented = false`.

### Added

- `skhll` and `skcms` — the load-bearing decision. The hash is a
  `fn(Bytes) -> Int` parameter, so this package chooses no hash for
  anyone and a caller that already hashes its keys pays for one pass.
  The sketch does not carry the function — that would make it
  unserialisable — but it carries the caller's LABEL for it, and a
  merge of two sketches with different labels is refused: two hashes
  put one item in two registers, and the merged sketch would count it
  twice with no error bound and no complaint.
- `sktdigest` — quantiles that are accurate where it matters, without
  anyone having chosen a bucket boundary in advance, and mergeable,
  which is what quantiles computed per instance are not. The minimum
  and the maximum are kept exactly. A quantile outside `0.0 ..= 1.0`
  is refused rather than clamped, because a caller that wrote `99.0`
  meant `0.99` and clamping answers the maximum and hides it.
- `skreservoir` — the one structure here that keeps the items. Its
  randomness arrives as uniform numbers the caller drew, and a merge is
  weighted by what each stream saw, because an unweighted merge of a
  million-item stream and a ten-item stream is uniform over nothing.
- `skfault` — eight refusals, with `is_merge_fault` separating the
  two that mean two producers disagree about their configuration from
  the six that mean a bad argument.

### Known

- `novo test` is red, and that is the release's expected state: every
  assertion in the API suite reaches `not implemented:
  sketch-nv.<module>.<fn>`.
- **The error bounds are the tests.** `1.04 / sqrt(2^precision)` for
  HyperLogLog++, `2 / width` at `1 - 0.5^depth` confidence for the
  count-min sketch. An implementation that does not meet them is not
  an implementation of this interface.
- **No top-K.** A count-min sketch cannot list what it has counted,
  only answer about an item it is shown. Finding the heavy hitters
  needs a heap of candidates beside it, and that is a separate value.
- **No theta sketch, and no HLL sparse-to-dense wire compatibility
  with any particular vendor.** `to_bytes` is this package's own form,
  carrying the parameters a merge has to check.
