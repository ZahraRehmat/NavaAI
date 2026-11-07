"""Prefer distinct spoken letter names before introducing acoustic neighbours."""
from grid_geometry import column_name

# One representative per conservative confusion group, in a fixed order.
# B represents the B/C/D/E/G/P/T/V/Z family; A represents A/J/K;
# F represents F/S/X; M represents M/N. English accents still differ.
PREFERRED='AFHILMOQRUWB'
DEFERRED=''.join(letter for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if letter not in PREFERRED)
ALPHABET=PREFERRED+DEFERRED
_TRANSLATION=str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ',ALPHABET)


def smart_label(index):
    """All 26 singles first, then pairs/triples in the same preferred order."""
    return column_name(index).translate(_TRANSLATION)
