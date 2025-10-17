# 🩸 Blood Bank Management System

A web-based Blood Bank Management System built using **Flask**, **PostgreSQL**, and **HTML/CSS**.  
This system provides separate dashboards for **Donors** and **Hospitals**, enabling real-time management of blood donations, inventory, and requests.

---

## 🚀 Features

### 🧑‍🤝‍🧑 Donor Module
- Register and log in securely.
- Schedule blood donations based on eligibility.
- View low-stock blood types to encourage referrals.
- Track donation history, eligibility for next donation, and total contributions.

### 🏥 Hospital Module
- Hospitals can request specific blood types and quantities.
- Real-time validation against the inventory.
- Automatic approval/denial of requests based on stock availability.
- Track past and current orders with statuses (`Pending`, `Approved`, `Denied`).
- Inventory updates automatically through a PostgreSQL trigger after fulfillment.

---

## 🗄️ Database Schema

The database consists of the following tables:

- **Users** – stores login and user details.  
- **Donors** – donor-specific info (blood group, DOB, last donation).  
- **Hospitals** – hospital profile and address.  
- **Blood_Inventory** – current stock of each blood group.  
- **Donations** – records donor blood donations.  
- **Hospital_Requests** – stores all hospital blood requests.  
- **Orders** – tracks order completion/failure.

All tables are normalized up to **BCNF (Boyce–Codd Normal Form)** ensuring data integrity and no redundancy.

---

## ⚙️ Database Setup

Run the following SQL scripts in PostgreSQL:

```sql
CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    user_type VARCHAR(10) CHECK (user_type IN ('Donor', 'Hospital')) NOT NULL
);

CREATE TABLE Donors (
    donor_id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    blood_group VARCHAR(5) NOT NULL,
    date_of_birth DATE NOT NULL,
    last_donation_date DATE
);

CREATE TABLE Hospitals (
    hospital_id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    hospital_name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL
);

CREATE TABLE Blood_Inventory (
    blood_group VARCHAR(5) PRIMARY KEY,
    quantity_ml INT DEFAULT 0 CHECK (quantity_ml >= 0)
);

CREATE TABLE Donations (
    donation_id SERIAL PRIMARY KEY,
    donor_id INT NOT NULL REFERENCES Donors(donor_id) ON DELETE CASCADE,
    blood_group VARCHAR(5) NOT NULL,
    quantity_ml INT NOT NULL CHECK (quantity_ml > 0),
    donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_blood_inventory FOREIGN KEY (blood_group) REFERENCES Blood_Inventory(blood_group) ON UPDATE CASCADE
);

CREATE TABLE Hospital_Requests (
    request_id SERIAL PRIMARY KEY,
    hospital_id INT NOT NULL REFERENCES Hospitals(hospital_id) ON DELETE CASCADE,
    blood_group VARCHAR(5) NOT NULL,
    quantity_ml INT NOT NULL CHECK (quantity_ml > 0),
    request_status VARCHAR(10) CHECK (request_status IN ('Pending', 'Approved', 'Denied')) DEFAULT 'Pending',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hospital_request_inventory FOREIGN KEY (blood_group) REFERENCES Blood_Inventory(blood_group) ON UPDATE CASCADE
);

CREATE TABLE Orders (
    order_id SERIAL PRIMARY KEY,
    request_id INT NOT NULL REFERENCES Hospital_Requests(request_id) ON DELETE CASCADE,
    fulfillment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    order_status VARCHAR(10) CHECK (order_status IN ('Completed', 'Failed')) NOT NULL
);
```

Stored procedure for processing hospital requests:

```sql
CALL fulfill_request(request_id);
```

Trigger to update inventory after fulfillment:

```sql
CREATE TRIGGER update_inventory_after_fulfillment
AFTER INSERT ON Orders
FOR EACH ROW
EXECUTE FUNCTION update_inventory_after_fulfillment();
```

---

## 💻 Tech Stack

| Layer | Technology |
|-------|-------------|
| Backend | Flask (Python) |
| Database | PostgreSQL |
| Frontend | HTML5, CSS3 |
| ORM/Connection | psycopg2 |
| Authentication | Flask Sessions, Password Hashing |

---

## ⚡ Setup & Run Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/krishnagarwal2204/bloodbank
   cd blood-bank-management
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # For Linux/Mac
   venv\Scripts\activate      # For Windows
   ```

3. **Install dependencies**
   ```bash
   pip install flask psycopg2-binary
   ```

4. **Update database connection**
   Edit your `app.py` connection function:
   ```python
   def get_connection():
       return psycopg2.connect(
           host="localhost",
           database="bloodbank",
           user="postgres",
           password="your_password"
       )
   ```

5. **Run the app**
   ```bash
   flask run
   ```
   Then open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📚 References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [PostgreSQL Official Docs](https://www.postgresql.org/docs/)
- [Jinja2 Template Engine](https://jinja.palletsprojects.com/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)

---
