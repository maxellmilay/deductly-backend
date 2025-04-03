# Camera API Documentation

## Image Management

**Endpoint:** `/camera/`

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
      "image_url": "string",
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
    "image_url": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "user": "integer",
    "image_url": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

**Endpoint:** `/camera/<id>/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "user": "integer",
    "image_url": "string",
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
    "user": "integer",
    "image_url": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "user": "integer",
    "image_url": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

### DELETE
- **Request Method:** DELETE
- **Request Body:** None
- **Expected Response Body:** None (204 No Content) 