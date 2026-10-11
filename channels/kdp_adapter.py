"""KDP adapter — canonical path per Universal Distribution Fabric Stage 01.

This is the directive-specified path (channels/kdp_adapter.py). The real
implementation lives in channels/kdp_arm.py (BaseArm contract, same pattern
as gumroad_arm/paddle_arm). This module re-exports it so either import path
works and exactly one registry entry ('kdp') exists.

    import channels.kdp_adapter  # directive path
    import channels.kdp_arm      # legacy path (also valid)

Both resolve to the same KdpArm class. Only kdp_arm.py self-registers;
this module does not re-register to avoid duplicate instances.
"""

from channels.kdp_arm import (  # noqa: F401
    KdpArm,
    KDP_HAS_API,
    KDP_EBOOK_FORMATS,
    KDP_PAPERBACK_TRIM_SIZES,
    KDP_EBOOK_MIN_PRICE,
    KDP_EBOOK_MAX_PRICE,
    ConfigError,
)

# Canonical alias per directive naming
KdpAdapter = KdpArm
