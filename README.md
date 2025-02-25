# Vad servicen gör

Servicen hanterar lagersaldot för produkterna och erbjuder endpoints för att hämta alla produkter, lägga till eller ta bort en produkt samt öka eller minska lagersaldot för specifika produkter.

Servicens endpoints kan man hitta och köra här (DEV-MILJÖ): https://dev-inventory-service-inventory-service.2.rahtiapp.fi/docs

# Endpoints

`GET /inventory` returnerar alla produkter som finns registerade i lager, även om produkten är slut.

```
  {
    "id": 0,
    "productCode": "string",
    "stock": 0
  }
```

`POST /inventory` lägger till en produkt i lagret. Du väljer produktkod och hur många av den som kommer finnas i lager.

```
  {
    "productCode": "string",
    "stock": 0
  }
```

`DELETE /inventory` raderar en produkt från lagret. För tillfället raderar den endast en produkt åt gången.

```
  {
    "productCode": "string"
  }
```

`PATCH /inventory/increase` ökar lagersaldo för en specifik produkt

```
  {
    "productCode": "string",
    "quantity": 0
  }
```

`POST /inventory/decrease` minskar lagersaldo för en specifik produkt. Denna kräver att man skickar email med endpointen för att kunna skicka bekräftelse till email-service.

```
  {
    "productCode": "string",
    "quantity": 0
  }
```

# Utvecklings miljö

Dependancies

```bash
pip install -r requirements.txt
```

Kopiera `.env-example` och namge till `.env`

Starta lokal postgres databas

```bash
docker compose up db
```

Starta APIn

```bash
docker compose up
```

# To-do

- Ändra `inventory/increase` att köra en POST istället, det matchar bättre med decrease endpointen
- Stöda arrays med POST och DELETE endpointen så man kan skicka/radera flera produkter på samma kallelse
- Ändra så GET använder samma objekt klass som POST (dvs ta bort att id fetchas)
- Lägga in unit tests för resterande endpoints
