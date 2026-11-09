"""Prefer distinct spoken letter names before introducing acoustic neighbours."""
def alphabetic_label(index):
    result='';index+=1
    while index:index,remainder=divmod(index-1,26);result=chr(65+remainder)+result
    return result

# One representative per conservative confusion group, in a fixed order.
# B represents the B/C/D/E/G/P/T/V/Z family; A represents A/J/K;
# F represents F/S/X; M represents M/N. English accents still differ.
PREFERRED='AFHILMOQRUWB'
DEFERRED=''.join(letter for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if letter not in PREFERRED)
ALPHABET=PREFERRED+DEFERRED
_TRANSLATION=str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ',ALPHABET)


def smart_label(index):
    """Reuse distinct letters in pairs instead of adding acoustic neighbours."""
    result='';index+=1
    while index:
        index,remainder=divmod(index-1,len(PREFERRED));result=PREFERRED[remainder]+result
    return result
