from flask import Flask, render_template, request, redirect, url_for, session,flash
import psycopg2
from psycopg2 import OperationalError
from psycopg2 import sql
from werkzeug.security import check_password_hash,generate_password_hash

app = Flask(__name__)
app.secret_key = 'bloodbank@#567'
# ----- Database Connection Function -----
def get_connection():
    try:
        conn = psycopg2.connect(
            dbname="blood_bank_db",
            user="postgres",          
            password="root",  
            host="localhost",
            port="5432"
        )
        print("Database connection successful.")
        return conn
    except OperationalError as e:
        print("Failed to connect to the database.")
        print(f"Error: {e}")
        return None

# ----- Test Route to Check DB Connection -----
@app.route('/test-db')
def test_db():
    conn = get_connection()
    if conn:
        conn.close()
        return "Connection to the database was successful!"
    else:
        return "Could not connect to the database."
    

@app.route('/')
def home():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id, password_hash, user_type FROM Users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['user_type'] = user[2]
            if user[2] == 'Donor':
                return redirect(url_for('donor_dashboard'))
            elif user[2] == 'Hospital':
                return redirect(url_for('hospital_dashboard'))
        else:
            return "Invalid credentials"

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        user_type = request.form['user_type']
        password_hash = generate_password_hash(password)

        conn = get_connection()
        cur = conn.cursor()

        try:
            # Insert into Users table
            cur.execute("""
                INSERT INTO Users (name, email, phone, password_hash, user_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id
            """, (name, email, phone, password_hash, user_type))
            user_id = cur.fetchone()[0]

            # Insert into Donors or Hospitals
            if user_type == 'Donor':
                blood_group = request.form['blood_group']
                date_of_birth = request.form['date_of_birth']
                cur.execute("""
                    INSERT INTO Donors (user_id, blood_group, date_of_birth)
                    VALUES (%s, %s, %s)
                """, (user_id, blood_group, date_of_birth))

            elif user_type == 'Hospital':
                hospital_name = request.form['hospital_name']
                address = request.form['address']
                cur.execute("""
                    INSERT INTO Hospitals (user_id, hospital_name, address)
                    VALUES (%s, %s, %s)
                """, (user_id, hospital_name, address))

            conn.commit()
            flash('Signup successful! You can now log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            flash(f'Error during signup: {e}', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('signup.html')

@app.route('/donor/dashboard')
def donor_dashboard():
    if session.get('user_type') != 'Donor':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.name, u.email, u.phone, d.blood_group, d.date_of_birth, d.last_donation_date
        FROM Users u JOIN Donors d ON u.user_id = d.user_id
        WHERE u.user_id = %s
    """, (session['user_id'],))
    donor = cur.fetchone()

    cur.execute("""
        SELECT blood_group FROM Blood_Inventory
        WHERE quantity_ml < 500
    """)
    low_stock = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('overview.html', donor=donor, low_stock=[b[0] for b in low_stock])

from datetime import datetime, timedelta

@app.route('/schedule-donation', methods=['GET', 'POST'])
def schedule_donation():
    if 'user_id' not in session or session.get('user_type') != 'Donor':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    # Get donor info
    cur.execute("""
        SELECT d.donor_id, d.blood_group, d.last_donation_date
        FROM Donors d
        JOIN Users u ON d.user_id = u.user_id
        WHERE u.user_id = %s
    """, (session['user_id'],))
    donor = cur.fetchone()

    if not donor:
        flash("Donor not found.", "error")
        return redirect(url_for('donor_dashboard'))

    donor_id, blood_group, last_donation_date = donor

    today = datetime.now().date()
    eligible = True
    next_eligible_date = None

    if last_donation_date:
        next_eligible_date = last_donation_date + timedelta(days=90)
        if today < next_eligible_date:
            eligible = False

    if request.method == 'POST':
        if eligible:
            quantity_ml = int(request.form['quantity_ml'])
            try:
                cur.execute("""
                    INSERT INTO Donations (donor_id, blood_group, quantity_ml)
                    VALUES (%s, %s, %s)
                """, (donor_id, blood_group, quantity_ml))
                conn.commit()
                flash("Donation scheduled successfully!", "success")
                return redirect(url_for('donation_history'))
            except Exception as e:
                conn.rollback()
                flash(f"Error scheduling donation: {e}", "error")
        else:
            flash("You are not yet eligible to donate. Please wait until your next eligible date.", "warning")

    cur.close()
    conn.close()

    return render_template('schedule_donation.html',
                           eligible=eligible,
                           next_eligible=next_eligible_date)

@app.route('/donor/history')
def donation_history():
    if session.get('user_type') != 'Donor':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    # Get donor ID from logged in user
    cur.execute("SELECT donor_id FROM Donors WHERE user_id = %s", (session['user_id'],))
    donor_row = cur.fetchone()
    if not donor_row:
        flash("Donor information not found.", "error")
        return redirect(url_for('donor_dashboard'))
    
    donor_id = donor_row[0]

    # Get donation history
    cur.execute("""
        SELECT donation_date, blood_group, quantity_ml
        FROM Donations
        WHERE donor_id = %s
        ORDER BY donation_date DESC
    """, (donor_id,))
    donations = cur.fetchall()

    # Get count and total amount
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(quantity_ml), 0)
        FROM Donations
        WHERE donor_id = %s
    """, (donor_id,))
    count, total_ml = cur.fetchone()

    # Get last donation date to calculate eligibility
    cur.execute("""
        SELECT MAX(donation_date)
        FROM Donations
        WHERE donor_id = %s
    """, (donor_id,))
    last_donation_date = cur.fetchone()[0]

    next_eligible = None
    if last_donation_date:
        from datetime import timedelta
        next_eligible = last_donation_date + timedelta(days=90)

    cur.close()
    conn.close()

    return render_template('donation_history.html',
                           donations=donations,
                           count=count,
                           total_ml=total_ml,
                           next_eligible=next_eligible)


@app.route('/hospital/dashboard')
def hospital_dashboard():
    if session.get('user_type') != 'Hospital':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    # Get hospital name
    cur.execute("""
        SELECT hospital_name FROM Hospitals 
        WHERE user_id = %s
    """, (session['user_id'],))
    hospital_name = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template('hospital_dashboard.html', hospital_name=hospital_name)

@app.route('/hospital/request', methods=['GET', 'POST'])
def make_request():
    if session.get('user_type') != 'Hospital':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        blood_group = request.form['blood_group']
        quantity_ml = int(request.form['quantity_ml'])

        # Get hospital_id
        cur.execute("SELECT hospital_id FROM Hospitals WHERE user_id = %s", (session['user_id'],))
        hospital_id = cur.fetchone()[0]

        # Step 1: Insert into Hospital_Requests and get the request_id
        cur.execute("""
            INSERT INTO Hospital_Requests (hospital_id, blood_group, quantity_ml)
            VALUES (%s, %s, %s)
            RETURNING request_id
        """, (hospital_id, blood_group, quantity_ml))
        request_id = cur.fetchone()[0]

        # Step 2: Call the stored procedure to process the request
        cur.execute("CALL fulfill_request(%s)", (request_id,))

        conn.commit()
        flash('Request submitted and processed successfully.')
        return redirect(url_for('track_orders'))

    cur.close()
    conn.close()
    return render_template('make_request.html')

@app.route('/hospital/orders')
def track_orders():
    if session.get('user_type') != 'Hospital':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT hospital_id FROM Hospitals WHERE user_id = %s", (session['user_id'],))
    hospital_id = cur.fetchone()[0]

    cur.execute("""
        SELECT hr.request_id, hr.blood_group, hr.quantity_ml, hr.request_status, hr.request_date, 
               o.fulfillment_date, o.order_status
        FROM Hospital_Requests hr
        LEFT JOIN Orders o ON hr.request_id = o.request_id
        WHERE hr.hospital_id = %s
        ORDER BY hr.request_date DESC
    """, (hospital_id,))
    orders = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('track_orders.html', orders=orders)

@app.route('/logout')
def logout():
    session.clear()  # This removes all data from the session
    flash('You have been logged out.', 'success')  # Optional: show a message
    return redirect(url_for('login'))

# ----- Run the Flask App -----
if __name__ == '__main__':
    app.run(debug=True)
