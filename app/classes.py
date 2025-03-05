from pydantic import BaseModel
from typing import List

class StockRequest(BaseModel):
    productCode: str
    quantity: int

class ProductDeleteRequest(BaseModel):
    productCode: str 

class DecreaseStockMultipleRequest(BaseModel):
    items: List[StockRequest]

class Product(BaseModel):
    productCode: str
    stock: int

class ProductCreate(BaseModel):
    productCode: str
    stock: int

class ProductDeleteMultipleRequest(BaseModel):
    productCodes: list[str]
