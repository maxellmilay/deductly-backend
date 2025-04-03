# Report API Documentation

## Report Management

**Endpoint:** `/report/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "id": "integer",
      "title": "string",
      "category": "string", // One of: "DAILY", "WEEKLY", "MONTHLY", "YEARLY"
      "start_date": "date",
      "end_date": "date",
      "grand_total_expenditure": "decimal",
      "total_tax_deductions": "decimal",
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
    "category": "string", // One of: "DAILY", "WEEKLY", "MONTHLY", "YEARLY"
    "start_date": "date",
    "end_date": "date",
    "grand_total_expenditure": "decimal",
    "total_tax_deductions": "decimal"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "category": "string",
    "start_date": "date",
    "end_date": "date",
    "grand_total_expenditure": "decimal",
    "total_tax_deductions": "decimal",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

**Endpoint:** `/report/<id>/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "category": "string",
    "start_date": "date",
    "end_date": "date",
    "grand_total_expenditure": "decimal",
    "total_tax_deductions": "decimal",
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
    "category": "string",
    "start_date": "date",
    "end_date": "date",
    "grand_total_expenditure": "decimal",
    "total_tax_deductions": "decimal"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "id": "integer",
    "title": "string",
    "category": "string",
    "start_date": "date",
    "end_date": "date",
    "grand_total_expenditure": "decimal",
    "total_tax_deductions": "decimal",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

### DELETE
- **Request Method:** DELETE
- **Request Body:** None
- **Expected Response Body:** None (204 No Content) 