# Third-party notices

Typoprint's first-party Python and Typst code is distributed under MIT. The generic
printing implementation was extracted from Editorial Lab with its owner's
authorization. Editorial Lab branding and application/workspace logic are excluded.

The following resources retain their original notices and licenses:

| Component | Version | License | Location |
| --- | --- | --- | --- |
| Typst Python binding | 0.15.0 | Apache-2.0 | Installed `typst` distribution; https://github.com/messense/typst-py |
| cmarker | 0.1.10 | MIT | `src/typoprint/resources/packages/preview/cmarker/0.1.10/LICENSE` |
| merman | 0.5.0 | MIT and bundled component notices | `src/typoprint/resources/packages/preview/merman/0.5.0/` |
| Source Sans 3 | 3.052R | SIL Open Font License 1.1 | `src/typoprint/resources/fonts/source-sans-3/OFL.txt` |

The merman distribution includes `THIRD_PARTY_NOTICES.md` and the complete
`THIRD_PARTY_LICENSES/` tree, including its embedded layout engines. Dagre is
selected for rendering; unused embedded components' notices are preserved.
Source Sans 3's `NOTICE.txt` records upstream locations and resource hashes.
Fonts embedded in the Typst wheel remain covered by that distribution's notices.
Pydantic is an installed dependency, not vendored code.

All bundled license and notice files ship in both wheel and source distributions.
