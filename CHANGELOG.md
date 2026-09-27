# Changelog

All notable changes to sketch-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## [0.1.0] — 2026-09-27

The first implementation of the interface published as 0.0.1.

### Added

- `skhll` counts distinct items with a 64-bit hash and Ertl's improved
  estimator (2017, algorithm 6). The estimator reads the histogram of
  register values, needs no empirical bias table, and agrees with
  linear counting for a handful of items. An estimate beyond the
  largest `Int` answers the largest `Int`.
- `skcms` places an item in each row at a column taken from the
  caller's hash mixed with the row number by the SplitMix64 finaliser.
  A count below one adds nothing.
- `sktdigest` is the merging t-digest with the `k1` scale function. A
  new observation is inserted as a centroid of its own, and the list is
  merged in one pass when it grows past the compression. The quantile
  and the rank interpolate as Dunning's reference implementation does.
  An empty digest answers `NaN`, and a `NaN` observation is not added.
- `skreservoir` is Vitter's algorithm R. A merge offers the sample of
  the stream that saw fewer items to the other, each item weighted by
  `seen / sample size`, as Apache DataSketches' reservoir union does.
- Each sketch serialises to its own form: a three-byte magic, a version
  byte, the parameters a merge checks, and the body.
- `tools/hll_reference.py`, a second implementation of the estimator,
  and suites that compare every sketch with exact answers on seeded
  streams.

### Changed

- `skfault.SkFault` gains `SkTooFewUniforms(needed, given)`, the
  refusal of a reservoir merge handed fewer uniform numbers than it
  needs. A `match` over `SkFault` that lists every variant needs the
  new arm.
- `sktdigest.quantiles` answers what `quantile` answers for each
  quantile. Its documentation no longer promises a single pass.
- The README no longer claims a build for a microcontroller. The
  sketches keep lists, and a build with no heap allocator refuses a
  list.
- The toolchain floor is 0.13.0.

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
