# Account API Documentation

## Google SSO Authentication

**Endpoint:** `/account/sso/google/`

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "id_token": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "token": "string"
  }
  ```

## User List

**Endpoint:** `/account/users/`

### GET
- **Request Method:** GET
- **Request Body:** None
- **Expected Response Body:**
  ```json
  [
    {
      "first_name": "string",
      "last_name": "string",
      "username": "string"
    }
  ]
  ```

## Authentication

**Endpoint:** `/account/authenticate/`

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "token": "string",
    "email": "string"
  }
  ```

## Registration

**Endpoint:** `/account/registration/`

### POST
- **Request Method:** POST
- **Request Body:**
  ```json
  {
    "username": "string",
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "password": "string"
  }
  ```
- **Expected Response Body:**
  ```json
  {
    "username": "string"
  }
  ``` 