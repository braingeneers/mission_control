# Bundled PyYAML

Version: 6.0.3 (Python 3.8+), MIT license; see PyYAML-LICENSE.
Upstream: https://github.com/yaml/pyyaml/tree/6.0.3
Source archive: https://files.pythonhosted.org/packages/05/8e/961c0007c59b8dd7729d542c61a4d537767a59645b82a0b521206e1e25c2/pyyaml-6.0.3.tar.gz
Archive SHA-256: `d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f`

The `yaml/` directory contains the unmodified `lib/yaml/*.py` files from
this archive, except `cyaml.py`, the optional compiled-extension adapter.
No compiled extension is bundled. The helper loads this package under a private
module name and uses `safe_load` for skill metadata. It needs no pip installation.
The local `.gitattributes` preserves upstream trailing whitespace and blank
lines so the bundled Python files remain byte-for-byte comparable to the source.

To refresh, download a reviewed upstream release, verify its published archive
checksum, replace the same pure Python files, retain its license, update this
notice, and run the maintenance and isolated-interpreter tests. Include all
bundled files in the normal skill integrity checks.
