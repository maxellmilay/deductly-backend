# Receipt API Documentation

## Receipt Management

**Endpoint:** `/receipt/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "id": "integer",
      "title": "string",
      "user": "integer",
      "category": "string", // One of: "FOOD", "TRANSPORTATION", "ENTERTAINMENT", "OTHER"
      "image": {
        "id": "integer",
        "title": "string",
        "user": "integer",
        "image_url": "string",
        "created_at": "datetime",
        "updated_at": "datetime"
      },
      "total_expediture": "decimal",
      "payment_method": "string",
      "vendor": {
        "id": "integer",
        "name": "string",
        "address": "string",
        "email": "string",
        "contact_number": "string",
        "establishment": "string",
        "date_created": "datetime",
        "date_updated": "datetime"
      },
      "discount": "decimal",
      "value_added_tax": "decimal",
      "document": {
        "id": "integer",
        "title": "string",
        "document_url": "string",
        "user": "integer",
        "type": "string",
        "created_at": "datetime",
        "updated_at": "datetime"
      },
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
  ```

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "title": "string",
    "user": "integer",
    "category": "string", // One of: "FOOD", "TRANSPORTATION", "ENTERTAINMENT", "OTHER"
    "image": {
      "id": "integer"
    },
    "total_expediture": "decimal",
    "payment_method": "string",
    "vendor": {
      "id": "integer"
    },
    "discount": "decimal",
    "value_added_tax": "decimal",
    "document": {
      "id": "integer"
    }
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "user": "integer",
    "category": "string",
    "image": {
      "id": "integer",
      "title": "string",
      "user": "integer",
      "image_url": "string",
      "created_at": "datetime",
      "updated_at": "datetime"
    },
    "total_expediture": "decimal",
    "payment_method": "string",
    "vendor": {
      "id": "integer",
      "name": "string",
      "address": "string",
      "email": "string",
      "contact_number": "string",
      "establishment": "string",
      "date_created": "datetime",
      "date_updated": "datetime"
    },
    "discount": "decimal",
    "value_added_tax": "decimal",
    "document": {
      "id": "integer",
      "title": "string",
      "document_url": "string",
      "user": "integer",
      "type": "string",
      "created_at": "datetime",
      "updated_at": "datetime"
    },
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

**Endpoint:** `/receipt/<id>/`

### GET, PUT, DELETE
- Similar to the above endpoint but for a specific receipt by ID.

## Vendor Management

**Endpoint:** `/vendor/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "id": "integer",
      "name": "string",
      "address": "string",
      "email": "string",
      "contact_number": "string",
      "establishment": "string",
      "date_created": "datetime",
      "date_updated": "datetime"
    }
  ]
  ```

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "name": "string",
    "address": "string",
    "email": "string",
    "contact_number": "string",
    "establishment": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "name": "string",
    "address": "string",
    "email": "string",
    "contact_number": "string",
    "establishment": "string",
    "date_created": "datetime",
    "date_updated": "datetime"
  }
  ```

**Endpoint:** `/vendor/<id>/`

### GET, PUT, DELETE
- Similar to the above endpoint but for a specific vendor by ID.

## Receipt Item Management

**Endpoint:** `/receipt-item/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "id": "integer",
      "title": "string",
      "quantity": "integer",
      "price": "decimal",
      "subtotal_expenditure": "decimal",
      "receipt": {
        "id": "integer",
        "title": "string",
        // ... receipt details
      },
      "deductable_amount": "decimal",
      "date_created": "datetime",
      "date_updated": "datetime"
    }
  ]
  ```

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "title": "string",
    "quantity": "integer",
    "price": "decimal",
    "subtotal_expenditure": "decimal",
    "receipt": "integer",
    "deductable_amount": "decimal"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "quantity": "integer",
    "price": "decimal",
    "subtotal_expenditure": "decimal",
    "receipt": {
      "id": "integer",
      "title": "string",
      // ... receipt details
    },
    "deductable_amount": "decimal",
    "date_created": "datetime",
    "date_updated": "datetime"
  }
  ```

**Endpoint:** `/receipt-item/<id>/`

### GET, PUT, DELETE
- Similar to the above endpoint but for a specific receipt item by ID. 