from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import UserMixin, login_user, logout_user, LoginManager, login_required, current_user
from flask_mail import Mail, Message
import json
from sqlalchemy import case, func

# Flask setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)



# SMTP mail server settings
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USERNAME='nandeesh.nandu2005@gmail.com',  # Correct access
    MAIL_PASSWORD='utua ufde ilpg aicp',  # Correct access
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=True,
)
mail=Mail(app)

# Flask-Login setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(customerID):
    return Customer.query.get(int(customerID))

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost:4307/car_rental_system'
db = SQLAlchemy(app)

# Define the Car model
class Car(db.Model):
    __tablename__ = 'Car'
    CarID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Model = db.Column(db.String(100), nullable=False)
    Category = db.Column(db.String(100), nullable=False)
    Status = db.Column(db.String(20), nullable=False)
    RentPrice = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(500), nullable=True)

# Define the Customer model
class Customer(UserMixin, db.Model):
    __tablename__ = 'Customer'
    customerID = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(1000), nullable=False)

    # Flask-Login requires this property for authentication
    @property
    def id(self):
        return self.customerID


# Define the Booking model
class Reservation(db.Model):
    __tablename__ = 'reservation'
    ReservationID = db.Column(db.Integer, primary_key=True)
    customerID = db.Column(db.Integer, db.ForeignKey('Customer.customerID'), nullable=False)
    carID = db.Column(db.Integer, db.ForeignKey('Car.CarID'), nullable=False)
    ReservationDate = db.Column(db.Date, nullable=False, default=db.func.current_date())
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    Status = db.Column(db.String(20), nullable=False)  # e.g., 'active', 'completed', 'cancelled'

# Define the Rental model
class Rental(db.Model):
    __tablename__ = 'rental'
    RentalID = db.Column(db.Integer, primary_key=True)
    carID = db.Column(db.Integer, db.ForeignKey('Car.CarID'), nullable=False)
    customerID = db.Column(db.Integer, db.ForeignKey('Customer.customerID'), nullable=False)
    StartDate = db.Column(db.Date, nullable=False)
    EndDate = db.Column(db.Date, nullable=False)
    TotalAmount = db.Column(db.Integer, nullable=False)  # Total price for the rental period
    Status = db.Column(db.String(20), nullable=True)  # e.g., 'active', 'completed', 'cancelled'

#Define the Payment model
class Payment(db.Model):
    __tablename__ = 'payment'
    PaymentID = db.Column(db.Integer, primary_key=True)
    RentalID = db.Column(db.Integer, db.ForeignKey('rental.RentalID'), nullable=False)
    Amount = db.Column(db.Integer, nullable=False)  # Amount paid
    Date = db.Column(db.Date, nullable=False, default=db.func.current_date())  # Date of payment
    Method = db.Column(db.String(50), nullable=False)  # e.g., 'completed', 'failed'
    TransactionNumber = db.Column(db.String(100), nullable=True)  # Unique transaction number for the payment


# Reservation Route
@app.route('/reservation/<CarID>', methods=['GET', 'POST'])
@login_required
def reservation(CarID):
    car = Car.query.get_or_404(CarID)  # Fetch car details or return 404 if not found
    
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        payment_method = request.form.get('payment_method')
        transaction_number = request.form.get('transaction_number')
        total_amount = request.form.get('total_amount')

        # Add reservation
        new_reservation = Reservation(
            customerID=current_user.customerID,
            carID=CarID,
            StartDate=start_date,
            EndDate=end_date,
            Status='Confirmed'
        )
        db.session.add(new_reservation)
        db.session.commit()

        # Add rental
        new_rental = Rental(
            carID=CarID,
            customerID=current_user.customerID,
            StartDate=start_date,
            EndDate=end_date,
            TotalAmount=total_amount,
            
        )
        
        db.session.add(new_rental)
        db.session.commit()

        # Add payment
        new_payment = Payment(
            RentalID=new_rental.RentalID,
            Amount=new_rental.TotalAmount,
            Date=db.func.current_date(),
            Method=payment_method,
            TransactionNumber=transaction_number
        )
        db.session.add(new_payment)
        db.session.commit()
        mail.send_message(
            subject="Reservation Confirmation",
            sender=app.config["MAIL_USERNAME"],
            recipients=[current_user.email],
            body=f"Hello {current_user.name},\n\nYour reservation for {car.Name} has been confirmed!\nPlease visit to our address on {start_date}\n\nContact:9901715162,8867264622,6302287329\n\nBest regards,\nGoDrive Rentals,\nHootagalli, Mysuru,\nKarnataka, India 570018"
        )
        flash('Reservation successful!', 'success')
        return redirect(url_for('menu'))

    return render_template('reservation.html', car=car, username=current_user.name)


@app.route('/reservations')
@login_required
def reservations():
    # Fetch all reservations for the logged-in user
    result = (
        db.session.query(Reservation, Rental, Payment, Car, Customer)
        .join(Rental, Reservation.ReservationID == Rental.RentalID)  # Correct join on ReservationID
        .join(Payment, Rental.RentalID == Payment.RentalID)
        .join(Car, Reservation.carID == Car.CarID)
        .join(Customer, Reservation.customerID == Customer.customerID)  # Ensure correct join on customerID
        .order_by(Reservation.ReservationID.desc())
        .all()
    )
    return render_template('reservations.html', results=result)

@app.route('/profile')
@login_required
def profile():
    # Fetch user details from the database
    customer = Customer.query.filter_by(customerID=current_user.customerID).first()
    return render_template('profile.html', customer=customer, username=current_user.name)


@app.route('/edit_profile',methods=['GET', 'POST'])
@login_required
def edit_profile():
    customer = Customer.query.filter_by(customerID=current_user.customerID).first()
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.contact = request.form.get('contactnumber')
        customer.email = request.form.get('email')
        customer.password = request.form.get('password')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', customer=customer)

@app.route('/')
def landing_page():
    return render_template('landing_page.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        customer = Customer.query.filter_by(email=email, password=password).first()
        if customer:
            login_user(customer)
            flash('Login successful!', 'success')
            # Distinguish between admin and user
            if email == '2023is_nandeesht_b@nie.ac.in' and password == 'Admin@123':
                return redirect(url_for('adminmenu'))
            return redirect(url_for('menu'))
        else:
            flash('Invalid email or password!', 'danger')
    return render_template('login.html')


# Reservation History Route
@app.route('/reservation_history')
@login_required
def reservation_history():
    # Fetch reservation, rental, and payment details for the logged-in user
    result = (
        db.session.query(Reservation, Rental, Payment, Car)
        .join(Rental, Reservation.ReservationID == Rental.RentalID)
        .join(Payment, Rental.RentalID == Payment.RentalID)
        .join(Car, Reservation.carID == Car.CarID)
        .filter(Reservation.customerID == current_user.customerID)
        .order_by(Reservation.ReservationID.desc())
        .all()
    )

    return render_template(
        'reservation_history.html',
        results=result,
        username=current_user.name,
    )


@app.route('/addcar', methods=['GET', 'POST'])
@login_required
def addcar():
    if current_user.email != '2023is_nandeesht_b@nie.ac.in':  # Restrict addcar to admin only
        flash('Access denied! Only admin can add cars.', 'danger')
        return redirect(url_for('menu'))

    if request.method == 'POST':
        name = request.form.get('name')
        model = request.form.get('model')
        category = request.form.get('category')
        status = request.form.get('status')
        rentprice = request.form.get('rentprice')
        image = request.form.get('image')

        new_car = Car(
            Name=name,
            Model=model,
            Category=category,
            Status=status,
            RentPrice=rentprice,
            image=image
        )
        db.session.add(new_car)
        db.session.commit()

        flash('Car added successfully!', 'success')
        return redirect(url_for('adminmenu'))
    return render_template('addcar.html')

@app.route('/editcar/<CarID>', methods=['GET', 'POST'])
@login_required
def editcar(CarID):
    car = Car.query.filter_by(CarID=CarID).first_or_404()  # Ensure valid CarID
    if current_user.email != '2023is_nandeesht_b@nie.ac.in':  # Restrict editcar to admin only
        flash('Access denied! Only admin can edit cars.', 'danger')
        return redirect(url_for('menu'))

    if request.method == 'POST':
        car.Name = request.form.get('name')
        car.Model = request.form.get('model')
        car.Category = request.form.get('category')
        car.Status = request.form.get('status')
        car.RentPrice = request.form.get('rentprice')
        car.image = request.form.get('image')

        db.session.commit()
        flash('Car details updated successfully!', 'success')
        return redirect(url_for('adminmenu'))
    return render_template('editcar.html', car=car)

@app.route('/deletecar/<CarID>', methods=['POST','GET'])
@login_required
def deletecar(CarID):
    car = Car.query.get_or_404(CarID)
    
    # Delete the car from the database
    db.session.delete(car)
    db.session.commit()
    flash('Car deleted successfully!', 'success')
    return redirect(url_for('adminmenu'))


@app.route('/adminmenu')
@login_required
def adminmenu():
    if current_user.email != '2023is_nandeesht_b@nie.ac.in':  # Restrict adminmenu to admin only
        flash('Access denied! Only admin can access this page.', 'danger')
        return redirect(url_for('menu'))

    query = Car.query.all()   
    return render_template('adminmenu.html', query=query)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle registration logic here
        username = request.form.get('username')
        contactnumber = request.form.get('contactnumber')
        email = request.form.get('email')
        password = request.form.get('password')
        confirmpassword = request.form.get('confirmpassword')
        
        # Check if email already exists
        customer = Customer.query.filter_by(email=email).first()
        if customer:
            flash('Email already exists!', 'danger')
            return render_template('register.html')
        
        if password != confirmpassword:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        # Save to database using SQLAlchemy ORM
        new_customer = Customer(
            name=username,
            contact=contactnumber,
            email=email,
            password=password  # Consider hashing the password before storing it
        )
        db.session.add(new_customer)
        db.session.commit()
        

        mail.send_message(
            subject="Welcome to GoDrive Rentals",
            sender=app.config["MAIL_USERNAME"],
            recipients=[email],
            body=f"Hello {username},\n\nThank you for registering with us!\n\nBest regards,\nGoDrive Rentals"
        )
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')





@app.route('/menu')
@login_required
def menu():
    query = Car.query.all()   
    return render_template('menu.html', username=current_user.name, query=query)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('landing_page'))

if __name__ == '__main__':
    app.run(debug=True)