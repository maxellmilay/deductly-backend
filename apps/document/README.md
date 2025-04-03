# Document API Documentation

## Document Management

**Endpoint:** `/document/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "id": "integer",
      "title": "string",
      "document_url": "string",
      "user": "integer",
      "type": "string", // One of: "RECEIPT", "INVOICE", "OTHER"
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
    "document_url": "string",
    "user": "integer",
    "type": "string" // One of: "RECEIPT", "INVOICE", "OTHER"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "document_url": "string",
    "user": "integer",
    "type": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

**Endpoint:** `/document/<id>/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "document_url": "string",
    "user": "integer",
    "type": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

### PUT
- **Request Method:** PUT
- **Request Body:**
  ```json
  {
    "title": "string",
    "document_url": "string",
    "user": "integer",
    "type": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "document_url": "string",
    "user": "integer",
    "type": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

### DELETE
- **Request Method:** DELETE
- **Request Body:** None
- **Expected Response Body:** None (204 No Content) 