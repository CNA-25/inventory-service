from fastapi import HTTPException
from typing import Dict, Optional
from app.classes import  *

# =============================
#  Om ni har funktioner som 
#  upprepas, lägg hit dem :)))
# =============================

def find_product_by_code(inventory: Dict[int, Product], product_code: str) -> Optional[int]:
    """Hitta produktens ID baserat på dess produktkod"""
    return next((key for key, product in inventory.items() if product.productCode == product_code), None)

# Ger error om produkten INTE finns
def check_product_exists(inventory: Dict[int, Product], product_code: str) -> int:
    """Checka att produkten finns i inventoryt, annars kasta ett HTTP 404-fel""" # tack dennis för du visa mig att man kan göra docstrings
    product_id = find_product_by_code(inventory, product_code)
    if product_id is None:
        raise HTTPException(status_code=404, detail=f"Produkten {product_code} finns inte")
    return product_id

# Ger error om PRODUKTEN FINNS   
def check_if_product_exists(inventory: Dict[int, Product], product_code: str):
    """skickar ett HTTP 400-fel om en produkt med samma produktkod redan finns."""
    if any(existing.productCode == product_code for existing in inventory.values()):
        raise HTTPException(
            status_code=400, 
            detail=f"Produkten med produktkod {product_code} finns redan."
        )
    
def ensure_valid_quantity(quantity: int):
    """Validera att kvantiteten är större än 0, annars kasta ett HTTP 400-fel"""
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Mängden måste vara större än 0")

    
def taivas():
    return """Katseet ylös luokaa veljet, aika tullut on,
Meidän edessämme vahvinkin on voimaton.
Aika pysähtyy ja siirtyy vuoret paikoiltaan,
Me emme järky vaikka tulta satais päälle maan.
Heikoille voi olla liikaa kutsu metallin,
Muttei niille joita ohjaa vaisto soturin!
Taivas lyö tulta yläpuolellamme,
Kaikuu kallioilla ääni totuuden.
Verivalan taika on aina suojanamme,
Tuo merkki metallisen veljeyden!
Missä liikummekin aina meidät huomataan,
Kunnia ja voima saavat meihin uskomaan.
Tulivana seuraa joukkoamme mahtavaa,
On luonto puolellamme tukemassa sanomaa:
Heikoille voi olla liikaa kutsu metallin,
Muttei niille joita ohjaa vaisto soturin!
Taivas lyö tulta yläpuolellamme,
Kaikuu kallioilla ääni totuuden.
Verivalan taika on aina suojanamme,
Tuo merkki metallisen veljeyden!
Taivas lyö tulta yläpuolellamme,
Kaikuu kallioilla ääni totuuden.
Taivas lyö tulta yläpuolellamme,
Kaikuu kallioilla ääni totuuden.
Verivalan taika on aina suojanamme,
Tuo merkki metallisen veljeyden!
Taivas lyö tulta!
Taivas lyö tulta!
Taivas lyö tulta yläpuolellamme,
Kaikuu kallioilla ääni totuuden.
Verivalan taika on aina suojanamme,
Tuo merkki metallisen veljeyden!"""