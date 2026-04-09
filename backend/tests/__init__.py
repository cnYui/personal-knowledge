"""Test package marker for stable intra-test imports.

This ensures imports like ``from tests.conftest import ...`` resolve to the
local backend test package instead of an unrelated third-party ``tests``
package installed in site-packages.
"""