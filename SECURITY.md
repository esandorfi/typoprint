# Security policy

## Supported versions

Security fixes go to the latest released version.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private reporting:
**Security → Report a vulnerability** on
<https://github.com/esandorfi/typoprint/security/advisories/new>.

Include the Typoprint version, a minimal input that reproduces the problem, and the
impact you expect. You can expect an acknowledgement within a few days.

## Scope

Typoprint treats Markdown as data and refuses remote images, embedded Typst, and
paths outside the render root. Reports about those boundaries are welcome. Custom
templates and Python callbacks are trusted developer code and are out of scope.
