# Rectangular-bar FE reference materials

This addition documents the supplied local reference project and its actual
archived calculations. It supplements the unchanged 9,000-row learning analysis;
the local cases are not replacement targets or proof of the full table's native
FE provenance.

## Files

| File | Purpose |
| --- | --- |
| [FE_REFERENCE_METHODS.md](FE_REFERENCE_METHODS.md) | Full methods extracted from the final revised Supplementary Methods, including material and loading tables |
| [Supplementary_Software_1.zip](Supplementary_Software_1.zip) | Compact source/evidence archive with its own 182-payload integrity manifest |
| [PACKAGE_README.md](PACKAGE_README.md) | Package instructions, including precise prepare-only commands; paths within it refer to the extracted archive |
| [reference_cases.csv](reference_cases.csv) | Three historical best-sampled strokes and unloaded deviations |
| [Supplementary_Software_1.zip.sha256](Supplementary_Software_1.zip.sha256) | SHA-256 of the downloadable archive |
| [THIRD_PARTY_DATA_NOTICE.txt](THIRD_PARTY_DATA_NOTICE.txt) | OPARA attribution and licence conditions |
| [raw_parse_verification.json](raw_parse_verification.json) | Historical read-only re-parsing receipt; required large raw fields are not in this compact archive |

## Use and limits

Download and extract the ZIP, then follow its README. Preparation uses Python
3.11 or later and the pinned NumPy 2.3.5; the exercised environment was Python
3.12.14. Run verify_package.py before preparing an input in a new empty directory.
The preparation wrapper never launches an FE solver. Full native warm replay
requires additional result/restart files, field exports and a configured MAPDL
environment, as described in the package.

The public ZIP corrects one packaging instruction from the earlier local review
copy: the minimum Python version is 3.11, matching NumPy 2.3.5. The copied original
source, material, case data and results are unchanged. The corrected README and
its manifest entry account for the changed archive checksum.

All three local examples retain formal qualification as false. The separate
public bending comparison concerns one specimen with 696 observation times;
it does not establish 696 independent experiments or MGRE-driven straightening
success. No new FE solve or ML fitting was performed to publish these materials.

The existing analytical-lineage audit is retained in [DATA_PROVENANCE.md](../DATA_PROVENANCE.md).
