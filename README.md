# sketch-nv

A **streaming sketch** answers a question about a stream of data in
memory that does not grow with the stream. It trades an exact answer
for a bounded approximate one: how many distinct items there were, how
often one item appeared, what the 99th percentile was, and a fair
sample of the items themselves. This package brings four of them to
novo-lang. The reference implementations are
[Apache DataSketches](https://datasketches.apache.org/), the Rust
crates [hyperloglogplus](https://docs.rs/hyperloglogplus) and
[tdigest](https://docs.rs/tdigest), and the papers each algorithm comes
from.

## What a sketch is

Counting a billion distinct visitors exactly takes a billion entries.
A sketch answers the same question in a few kilobytes, with an error
that is **published**: a number the caller can state alongside the
answer, not a hope.

| Sketch | Question | Memory | Error |
| --- | --- | --- | --- |
| HyperLogLog | How many distinct items? | `2^precision` registers | `1.04 / sqrt(2^precision)` relative |
| Count-min | How often did this item appear? | `width x depth` counters | Never low; high by `2/width` of the total, with probability `0.5^depth` |
| t-digest | What is the *q*th percentile? | About `compression` centroids | Smallest at the extremes |
| Reservoir | Show me *k* of the items | `k` items | A uniform sample, exactly |

Three properties make these worth having over exact counting, and all
three are in the interface.

They are **mergeable**: the sketch of two streams can be computed from
the sketch of each. A hundred machines each keep a sketch, and the
union is as accurate as one sketch of everything. Exact distinct counts
and per-machine percentiles cannot be combined that way — the mean of
two 99th percentiles is not the 99th percentile of anything.

They are **serialisable**: a sketch can be stored in a row, sent over a
wire, and merged a week later.

And their error is **stated**, so a caller can report "about 4.1
million, within 1.6%".

The three hashed sketches need a 64-bit hash. **That hash is the
caller's**, passed in as a function. The sketch carries the caller's
*name* for it, and refuses to merge with a sketch built under a
different name.

## Install

```
novo pkg add sketch-nv
```

## Example

```novo
use skhll

// The caller's 64-bit hash. In a real program this is xxhash-nv's
// XXH3, or whatever the program already hashes its keys with.
fn visitor_hash(b: Bytes) -> Int
    bytes.len(b) * 2654435761

fn main() [io]
    // Precision 12: 4096 registers, about 1.6% relative error.
    match skhll.new(12, "visitor_hash")
        Err(f) => println("bad precision: ${f.message()}")
        Ok(empty) =>
            // Every item goes through the same hash.
            let one = skhll.add(empty, bytes.from_str("ada"), visitor_hash)
            let two = skhll.add(one, bytes.from_str("grace"), visitor_hash)

            // The estimate, and the error to report beside it.
            println("about ${skhll.estimate(two)} distinct visitors")
            println("within ${skhll.relative_error(two)}")

            // Two shards' sketches make one answer for both.
            match skhll.merge(two, empty)
                Ok(u)  => println("both shards: ${skhll.estimate(u)}")
                Err(f) => println("cannot merge: ${f.message()}")
```

Build and test with `novo pkg build` and `novo test`.

## What the package contains

| Module | Contents |
| --- | --- |
| `skfault` | The eight ways a sketch or a merge can be refused. |
| `skhll` | HyperLogLog over a 64-bit hash: distinct counting, its error bound and its merge. |
| `skcms` | The count-min sketch: frequency estimation, its one-sided error, and the halving that ages it. |
| `sktdigest` | The t-digest: quantiles, ranks, the exact extremes and the merge. |
| `skreservoir` | Reservoir sampling: a uniform sample of the items themselves. |

## How to choose an entry point

**`skhll` counts distinct things** — visitors, addresses, identifiers.
It cannot tell you whether one particular item was seen; that is a
Bloom filter's question.

**`skcms` counts how often**, and its error is one-sided: the estimate
is never below the truth. That is what a heavy-hitter detector and a
cache admission policy need.

**`sktdigest` answers percentiles** over a distribution whose range
nobody chose in advance. Take a Prometheus histogram instead when the
buckets are known and fixed; take this when the 99.9th percentile
matters.

**`skreservoir` keeps the items**, not a number. Take it when the
answer is "show me some".

**`add_hashed` and `estimate_hashed` are for a caller that already
hashed the item** for another reason, and should not pay twice.

## The rules a user needs

1. **The hash is yours, and it must be the same one every time.** A
   sketch fed through two hashes counts some items twice.
2. **Name the hash.** The label passed to `new` is compared on every
   merge and interpreted nowhere. Two sketches with different labels do
   not merge.
3. **Merging needs identical parameters.** Precisions, table shapes and
   compressions must match. `skfault.is_merge_fault` separates those
   refusals from bad arguments, because they mean two producers
   disagree about their configuration.
4. **HyperLogLog's precision is 4 to 18.** Below four the estimate is
   noise; above eighteen the registers are larger than the exact set
   would have been.
5. **A HyperLogLog estimate is exact for a handful of items.** The
   estimator is Ertl's improved estimator (2017, algorithm 6), which
   agrees with linear counting for small counts and needs no empirical
   bias table. It becomes approximate as the count grows.
6. **A count-min estimate is never too low.** It is too high by more
   than `error_bound x total` with probability at most
   `1 - confidence`.
7. **Size a count-min sketch from the error, not the table.**
   `with_error(epsilon, delta, …)` takes the two numbers a caller can
   reason about (Cormode and Muthukrishnan's sizing).
8. **A count-min sketch cannot list what it counted.** Finding the top
   items needs a heap of candidates kept beside it.
9. **A count-min sketch forgets by halving.** A stream running for a
   week otherwise answers about the whole week. `skcms.halve` is the
   call, and the caller chooses when — nothing here reads a clock.
10. **A t-digest's error is smallest at the extremes**, which is where
    the 99.9th percentile is. That is the property a fixed-bucket
    histogram does not have.
11. **A t-digest's minimum and maximum are exact.** Quantile `0.0` is
    the smallest observation and `1.0` the largest.
12. **A quantile is a fraction in `0.0 ..= 1.0`.** `99.0` is refused,
    not clamped: clamping would answer the maximum and hide the
    mistake.
13. **Compression is 20 to 1000.** A hundred is the usual choice.
14. **A reservoir's randomness is the caller's.** `offer` takes a
    uniform number in `0.0 ..< 1.0`, and `needs_uniform` says whether
    the next offer will use one.
15. **Report the reservoir's `seen_of` with its sample.** Three errors
    in a sample of a hundred drawn from a million offers is thirty
    thousand errors.
16. **A reservoir merge is weighted by what each stream saw.** An
    unweighted merge of a million-item stream and a ten-item stream is
    uniform over nothing. It takes one uniform number per item held by
    the reservoir that saw fewer items, and refuses a shorter list.
17. **Every call that adds answers a new sketch.** The sketch passed in
    is left unchanged, so an add copies what it changes. An add to a
    HyperLogLog costs time in proportion to `2^precision` when it raises
    a register, and an add to a count-min sketch in proportion to
    `width x depth`.
18. **An empty t-digest has no quantile.** `quantile` and `rank` answer
    `NaN` for it, and a `NaN` observation is not added.

## What is not included

- **A hash function.** See rule 1. A caller that already has one should
  not get a second, and pinning one here would pin every consumer.
- **A random number generator.** See rule 14.
- **A clock.** `skcms.halve` is the ageing step, and when to call it is
  the caller's decision.
- **Top-K.** See rule 8.
- **Wire compatibility with another implementation's serialised form.**
  `to_bytes` is this package's own, carrying the parameters a merge
  checks.
- **A build for a microcontroller.** The registers, counters,
  centroids and items are lists, and a build with no heap allocator
  refuses a list. A device keeps the counts it needs and hands them to
  a host that sketches.
- **Theta sketches, and set intersection.** HyperLogLog unions
  exactly; intersecting two of them is a different family with a
  different error bound.

## Related packages

- [xxhash-nv](https://novo-lang.org/packages/xxhash-nv) is a fast
  64-bit hash to pass in. So is crypto-nv's SHA-256, when the input is
  adversarial.
- [bloom-nv](https://novo-lang.org/packages/bloom-nv) answers the
  question these do not: whether one particular item has been seen.
- [prometheus-nv](https://novo-lang.org/packages/prometheus-nv) takes
  the quantiles a t-digest computes, for a summary metric.
- [stats-nv](https://novo-lang.org/packages/stats-nv) is for a dataset
  that fits in memory, where an exact quantile costs a sort.

## Tests

```bash
novo test tests/skhll_tests.nv       # the two hashed sketches and their bounds
novo test tests/sktdigest_tests.nv   # quantiles, the exact extremes, and the reservoir
novo test tests/skaccuracy_tests.nv  # every sketch against exact answers on seeded streams
novo test tests/skedge_tests.nv      # refusals, messages and interpolation corner cases
bash tests/coverage.sh               # line coverage over src/, merged across the suites
```

The normative sources are Flajolet, Fusy, Gandouet and Meunier's
HyperLogLog (2007) with the 64-bit hash of Heule, Nunkesser and Hall's
HyperLogLog++ (2013), Ertl's improved estimator (2017), Cormode and
Muthukrishnan's count-min sketch (2005), Dunning and Ertl's t-digest
(2019), and Vitter's algorithm R for reservoir sampling (1985).

The suites check these things:

- HyperLogLog registers against hand-worked hashes, and estimates on
  eight seeded streams against `tools/hll_reference.py`, a second
  implementation of Ertl's estimator written from the paper. Each
  estimate is also within three standard errors of the true count, and
  the error over sixteen streams is within 1.5 times
  `1.04 / sqrt(2^precision)`.
- A merge of two HyperLogLog sketches equals the sketch of both streams,
  register for register.
- No count-min estimate is below the exact count, and the share of
  items estimated further above than `error_bound x total` is at most
  `1 - confidence`.
- t-digest quantiles on a uniform and an exponential stream of 20,000
  values, and on four merged digests, are within a rank tolerance of
  the exact sorted stream: 0.0005 at the 0.1st and 99.9th percentiles,
  0.01 at the median. The interpolation cases are worked by hand from
  Dunning's reference implementation.
- Over 2,000 seeded runs, every item of a stream is kept by a
  reservoir within four standard deviations of the expected number of
  times, and a merge of a 90-item stream with a 10-item stream keeps
  about one item of the short one.
- Every refusal, including every malformed serialised form.

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
