# **User Management API Documentation**

## **Overview**

This API handles **User Registration, Authentication (Login), Student CRUD operations, and Room Management** in a Django REST Framework (DRF) application.

---

## **1️⃣ User Registration**

### **Endpoint:**

`POST /auth/register/`

### **Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "username": "johndoe",
  "email": "johndoe@gmail.com",
  "password": "StrongPass123!",
  "confirm_password": "StrongPass123!",
  "admission_number": "ADM001",
  "year_of_admission": 2023,
  "faculty": "Engineering",
  "course": "Software Engineering",
  "institution": "XYZ University",
  "phone_number": "1234567890"
}
```

### **Validations Implemented:**

✅ `password == confirm_password`
✅ Unique `admission_number`
✅ Password must contain **at least one uppercase letter, one lowercase letter, one number, one special character, and be at least 8 characters long**

### **Response:**

```json
{
  "message": "User registered successfully"
}
```

---

## **2️⃣ User Login**

### **Endpoint:**

`POST /auth/login/`

### **Request Body:**

```json
{
  "username": "johndoe", 
  "password": "StrongPass123!"
}
```

### **Response:**

```json
{
  "message": "Login successful",
  "token": "your-generated-token"
}
```

✅ **Users can log in using either ****`username`**** or ****`email`****.**
✅ **A token is generated and returned in the response.**

---

## **3️⃣ Student CRUD Operations**

### **Create Student (Handled in Registration)**

### **Get All Students**

`GET /users/students/`

#### **Response:**

```json
[
  {
    "id": 1,
    "user": {  
        "id": 3,
        "username": "johndoe"
    },
    "admission_number": "ADM001",
    "year_of_admission": 2023,
    "faculty": "Engineering",
    "course": "Software Engineering",
    "institution": "XYZ University",
    "phone_number": "1234567890"
  }
]
```

✅ **Password is completely hidden**

---

### **Get Student by ID**

`GET /users/students/{id}/`

#### **Response:**

```json
{
  "id": 1,
  "user": {  
        "id": 3,
        "username": "johndoe"
    },
  "admission_number": "ADM001",
  "year_of_admission": 2023,
  "faculty": "Engineering",
  "course": "Software Engineering",
  "institution": "XYZ University",
  "phone_number": "1234567890"
}
```

---

### **Update Student Details**

(`PUT or POST) /users/students/{id}/`

#### **Allowed Updates:**

- `admission_number`
- `year_of_admission`
- `faculty`
- `course`
- `institution`
- `phone_number`

✅ **Users can only update ****`Student`**** fields (not ****`User`**** fields like ****`username`****, ****`email`****, etc.)**

### **Request Body:**

```json
{
  "admission_number": "ADM002",
  "year_of_admission": 2024,
  "faculty": "Science",
  "course": "Data Science",
  "institution": "XYZ University",
  "phone_number": "0987654321"
}
```

#### **Response:**

```json
{
  "message": "Student details updated successfully."
}
```

✅ **Password is NOT returned in any response.**

---

### **Delete Student**

`DELETE /users/students/{id}/`

#### **Response:**

```json
{
  "message": "Student deleted successfully."
}
```

✅ **Deletes student profile but keeps the associated User account.**

---

## **4️⃣ Room Management**

### **Create a Room**

`POST /rooms/`

#### **Request Body:**

```json
{
  "name": "Study Group",
  "description": "A group for CS students.",
  "institution": "XYZ University"
}
```

#### **Response:**

```json
{
  "id": 1,
  "name": "Study Group",
  "description": "A group for CS students.",
  "institution": "XYZ University",
  "created_by": "johndoe",
  "created_on": "2025-02-22T08:58:30Z",
  "invitation_code": "ABC123XYZ"
}
```

---

### **Get All Rooms**

`GET /rooms/`

#### **Response:**

```json
[
  {
    "id": 1,
    "name": "Study Group",
    "description": "A group for CS students.",
    "institution": "XYZ University",
    "created_by": "johndoe",
    "created_on": "2025-02-22T08:58:30Z",
    "invitation_code": "ABC123XYZ"
  }
]
```

---

### **Update a Room**

`PUT /rooms/{id}/`

#### **Allowed Updates:**

- `name`
- `description`
- `institution`

#### **Response:**

```json
{
  "message": "Room updated successfully."
}
```

---

### **Delete a Room**

`DELETE /rooms/{id}/`

#### **Response:**

```json
{
  "message": "Room deleted successfully."
}
```

---

## **5️⃣ URL Patterns**

```python
auth/register/  "register a user"
auth/login/      "login a user"
users/           "view the list of all users in the system."
users/<int:pk>/  "CRUD for the user. POST and PUT perform UPDATE operation."
users/students/  "view a list of all students in the system."
users/students/<int:pk>/ "CRUD for the student. POST and PUT perform the same operation."
rooms/           "view a list of all rooms and create new rooms."
rooms/<int:pk>/  "CRUD for the room. PUT perform UPDATE operation."
```

---

## **✅ Summary of What’s Implemented**

✔ **User registration with strong password validation**

✔ **Login with username/email & password (Token Authentication)**

✔ **CRUD operations for students**

✔ **CRUD operations for rooms**

✔ **Restricted updates (Users cannot modify their own User model details)**

✔ **Secure password storage & API data handling**

✔ **Added API's for Rooms mangegment(CRUD) operations.**

