# **User Management API Documentation**

## **Overview**

This API handles **User Registration, Authentication (Login), and User & Student CRUD operations** in a Django REST Framework (DRF) application.

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
  "username": "johndoe", # You can add the email too.
  "password": "StrongPass123!"
}
```

### **Response:**

```json
{
  "message": "Login successful",
  "username": "johndoe"
}
```

✅ **Users can log in using either ************************************************************************************************************************************************`username`************************************************************************************************************************************************ or ************************************************************************************************************************************************`email`************************************************************************************************************************************************.**

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
        "username": "johndoe",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@gmail.com"
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
        "username": "johndoe",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@gmail.com"
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

✅ **Users can only update ************************************************************************************************************************************************`Student`************************************************************************************************************************************************ fields** (not `User` fields like `username`, `email`, etc.)

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

## **4️⃣ User CRUD Operations**

### **Get All Users**

`GET /users/`

#### **Response:**

```json
[
  {  
      "id": 3,
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "email": "johndoe@gmail.com"
  },
]

```

---

### **Get User by ID**

`GET /users/{id}/`

#### **Response:**

```json
{  
    "id": 3,
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "email": "johndoe@gmail.com"
},
```

---

### **Update User Details**

(`PUT or POST) /users/{id}/`

#### **Allowed Updates:**

- `first_name`
- `last_name`
- `email`
- `username`



### **Request Body:**

```json
{  
    "id": 3,
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "email": "johndoe@gmail.com"
},
```

#### **Response:**

```json
{
  "message": "User details updated successfully."
}
```

---

### **Delete User**

`DELETE /users/{id}/`

#### **Response:**

```json
{
  "message": "User deleted successfully."
}
```

✅ **Deleting a user also deletes the associated student profile.**

---

## **5️⃣ URL Patterns**

```python
auth/register/  "register a user"
auth/login/      "login a user"
users/           "view the list of all users in the system."
users/<int:pk>/  "CRUD for the user. POST and PUT perform UPDATE operations"
users/students/  "view a list of all the students in the system."
users/students/<int:pk>/ "CRUD for the student. POST and PUT perform the same operation."
```

---

## **6️⃣ Security & Data Handling**

✅ **Passwords are hashed using Django’s built-in hashing system.** ✅ Sensitive fields `password` are hidden from responses.

✅ When updating a student’s details, the user cannot be updated.

---

## **✅ Summary of What’s Implemented**

✔ **User registration with strong password validation**

✔ **Login with username/email & password**

✔ **CRUD operations for users and students**

✔ **Restricted updates (Users cannot modify their own User model details)**


✔ **Secure password storage & API data handling**

