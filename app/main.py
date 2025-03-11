import os
from typing import List
from databases import Database
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.openapi.utils import get_openapi
from app.classes import Product, ProductCreate, StockRequest, DecreaseStockMultipleRequest, ProductDeleteRequest
from app.utils import ensure_valid_quantity
from app.auth.dependencies import get_current_user, get_current_admin_user
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================
#           DATABASE
#           
# =============================

DATABASE_URL = os.getenv("DATABASE_URL")
database = Database(DATABASE_URL)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect() 

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Inventory API",
        version="1.0.0",
        description="API for managing inventory",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi 

# =============================
#           INVENTORY
#         get/post/delete      
# =============================

@app.get("/inventory", response_model=list[Product], tags=["Inventory"])
async def get_full_inventory_stock():
    query = "SELECT id, sku, stock FROM products"
    rows = await database.fetch_all(query)
    products = [Product(productCode=row["sku"], stock=row["stock"]) for row in rows]
    return products

@app.get("/inventory/", response_model=List[Product], tags=["Inventory"])
async def get_stock_for_multiple_products(
    productCodes: List[str] = Query(..., example=["foo", "bar"])
):
    query = "SELECT id, sku, stock FROM products WHERE sku = ANY(:codes)"
    rows = await database.fetch_all(query, values={"codes": tuple(productCodes)})
    if not rows:
        raise HTTPException(status_code=404, detail="Produkter finns inte")
    return [Product(productCode=row["sku"], stock=row["stock"]) for row in rows]

@app.post("/inventory", response_model=list[Product], status_code=201, tags=["Inventory Management"])
async def create_products(
    products: list[ProductCreate],
    admin: dict = Depends(get_current_admin_user)
):
    new_products = []
    for product in products:
        query = """
            INSERT INTO products (sku, stock) 
            VALUES (:productCode, :stock) 
            RETURNING id, sku, stock
        """
        row = await database.fetch_one(query, values={"productCode": product.productCode, "stock": product.stock})
        new_products.append(Product(productCode=row["sku"], stock=row["stock"]))
    return new_products

@app.delete("/inventory", status_code=200, tags=["Inventory Management"])
async def delete_products(
    requests: list[ProductDeleteRequest],
    admin: dict = Depends(get_current_admin_user)
):
    messages = []
    for request in requests:
        query = "SELECT id, sku FROM products WHERE sku = :productCode"
        row = await database.fetch_one(query, values={"productCode": request.productCode})
        if row is None:
            raise HTTPException(status_code=404, detail=f"Produkten {request.productCode} finns inte")
        delete_query = "DELETE FROM products WHERE sku = :productCode"
        await database.execute(delete_query, values={"productCode": request.productCode})
        messages.append(f"Produkten {request.productCode} är borttagen")
    return {"message": messages}

# =============================
#        INVENTORY SALDO
#        öka/sänka saldo
# =============================

@app.post("/inventory/increase", response_model=Product, tags=["Stock Management"])
async def increase_stock(
    request: StockRequest,
    admin: dict = Depends(get_current_admin_user)
):
    query = "SELECT id, sku, stock FROM products WHERE sku = :productCode"
    row = await database.fetch_one(query, values={"productCode": request.productCode})
    if row is None:
        raise HTTPException(status_code=404, detail=f"Produkten {request.productCode} finns inte")
    ensure_valid_quantity(request.quantity)
    update_query = """
        UPDATE products SET stock = stock + :quantity 
        WHERE sku = :productCode 
        RETURNING id, sku, stock
    """
    updated = await database.fetch_one(update_query, values={"quantity": request.quantity, "productCode": request.productCode})
    return Product(productCode=updated["sku"], stock=updated["stock"])

@app.post("/inventory/decrease", response_model=list[Product], tags=["Stock Management"])
async def decrease_stock(
    request: DecreaseStockMultipleRequest, 
    user: dict = Depends(get_current_user)
):
    async with database.transaction():
        updated_products = []
        shipped_info = []  # store the ordered quantities
        for item in request.items:
            query = "SELECT id, sku, stock FROM products WHERE sku = :productCode FOR UPDATE"
            row = await database.fetch_one(query, values={"productCode": item.productCode})
            if row is None:
                raise HTTPException(status_code=404, detail=f"Produkten {item.productCode} finns inte")
            ensure_valid_quantity(item.quantity)
            if row["stock"] < item.quantity:
                raise HTTPException(status_code=400, detail=f"Inte tillräckligt med lagersaldo för {item.productCode}")
            update_query = """
                UPDATE products SET stock = stock - :quantity 
                WHERE sku = :productCode 
                RETURNING id, sku, stock
            """
            updated = await database.fetch_one(update_query, values={"quantity": item.quantity, "productCode": item.productCode})
            updated_products.append(Product(productCode=updated["sku"], stock=updated["stock"]))
            shipped_info.append({"productCode": item.productCode, "quantity": item.quantity})
        if "admin" not in user.get("role", []):
            await send_shipping_confirmation(user["token"], shipped_info)
        return updated_products

# =============================
#           SHIPPING
#     Kalla på shipping api
# =============================

async def send_shipping_confirmation(token: str, shipped_info: list[dict]):
    items_details = "<br>".join([f"{item['productCode']}: {item['quantity']} st" for item in shipped_info])
    body = f"""
<html>
  <body>
    <p>Hej,</p>
    <p>Din beställning har nu skickats med följande varor:</p>
    <p>{items_details}</p>
    <p>Mvh, Beercraft</p>
  </body>
</html>
"""
    subject = "Beställning skickad"
    response = requests.post(
        'https://email-service-git-email-service-api.2.rahtiapp.fi/shipping',
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            'subject': subject,
            'body': body
        }
    )
    if response.status_code == 200:
        print("Försändelsebekräftelse skickad")
    else:
        print(f"Kunde inte skicka försändelsebekräftelse: {response.text}")