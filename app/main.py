from databases import Database
from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from app.classes import  *
from app.inventory import inventory
from app.utils import *
from app.auth.dependencies import *

app = FastAPI()

# =============================
#           DATABASE
#           
# =============================

MODE = os.getenv("MODE")
DATABASE_URL = os.getenv("DATABASE_URL_DEV") if MODE == "development" else os.getenv("DATABASE_URL_PROD")
#DATABASE_URL = "postgresql://postgres:root@host.docker.internal:5432/product-inventory" # LOCAL
database = Database(DATABASE_URL)

@app.on_event("startup")
async def startup():
    await database.connect()
    query = """
    CREATE TABLE IF NOT EXISTS Products (
        Id SERIAL PRIMARY KEY,
        SKU VARCHAR(100) UNIQUE NOT NULL,
        Stock INT NOT NULL,
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now()
    );
    """
    await database.execute(query=query)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect() 

@app.get("/testConnection") # Test connection.
async def read_root():
    query = "SELECT * FROM products"
    results = await database.fetch_all(query)
    return {"results": results}

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
def get_inventory(user: dict = Depends(get_current_user)):
    return list(inventory.values())

@app.get("/inventory/{productCode}", tags=["Inventory"])
def get_product_stock(productCode: str, user: dict = Depends(get_current_user)):
    product_id = check_product_exists(inventory, productCode)
    product = inventory[product_id]
    return {"productCode": product.productCode, "stock": product.stock}

@app.post("/inventory", response_model=List[Product], status_code=201, tags=["Inventory Management"])
def create_products(
    products: List[Product],
    admin: dict = Depends(get_current_admin_user)
):
    new_products = []
    for product in products:
        new_id = max(inventory.keys(), default=0) + 1  
        new_product = Product(id=new_id, productCode=product.productCode, stock=product.stock)
        inventory[new_id] = new_product
        new_products.append(new_product)
    return new_products

@app.delete("/inventory", status_code=200, tags=["Inventory Management"])
def delete_products(
    requests: List[ProductDeleteRequest],
    admin: dict = Depends(get_current_admin_user)
):
    messages = []
    for request in requests:
        product_id = check_product_exists(inventory, request.productCode)
        deleted_product = inventory.pop(product_id)
        messages.append(f"Produkten {deleted_product.productCode} är borttagen")
    return {"message": messages}


# =============================
#        INVENTORY SALDO
#        öka/sänka saldo
# =============================

@app.post("/inventory/increase", response_model=Product, tags=["Stock Management"])
def increase_stock(
    request: StockRequest,
    admin: dict = Depends(get_current_admin_user)
):
    product_id = check_product_exists(inventory, request.productCode)
    ensure_valid_quantity(request.quantity)

    inventory[product_id] = inventory[product_id].model_copy(update={"stock": inventory[product_id].stock + request.quantity})
    return inventory[product_id]

@app.post("/inventory/decrease", response_model=List[Product], tags=["Stock Management"])
def decrease_stock(
    request: DecreaseStockMultipleRequest, 
    user: dict = Depends(get_current_user)
):
    """
    Decreases stock for multiple products.
    Requires admin authentication via JWT.
    """
    updated_products = []

    for item in request.items:
        product_id = check_product_exists(inventory, item.productCode)
        ensure_valid_quantity(item.quantity)

        product = inventory[product_id]
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Inte tillräckligt med lagersaldo för {item.productCode}")

        inventory[product_id] = product.model_copy(update={"stock": product.stock - item.quantity})
        updated_products.append(inventory[product_id])

    send_shipping_confirmation(request.email, updated_products)
    return updated_products

# =============================
#           SHIPPING
#     Kalla på shipping api
# =============================

def send_shipping_confirmation(
        email: str, 
        products: list[Product],
        user: dict = Depends(get_current_user)
        ):
    print(f"Skickar shippingbekräftelse till {email} för produkterna:")
    for product in products:
        print(f"{product.productCode}: {product.stock}st")