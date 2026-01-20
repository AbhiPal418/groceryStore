from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, session
import csv
from io import TextIOWrapper
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


db = SQLAlchemy(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200), default="default.webp")


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)

    product = db.relationship('Product')


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='Placed')

    customer = db.relationship('Customer')
    items = db.relationship('OrderItem', backref='order')
    date = db.Column(db.DateTime, default=datetime.utcnow)



class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.String(100))

    product = db.relationship('Product')


with app.app_context():
    db.create_all()


def fine(s):
    ans = ""
    for ch in s:
        if(ch >= '0' and ch <= '9'):
            ans = ans + ch

    return int(ans)


@app.route("/")
def index():
    query = request.args.get("q")

    if query:
        products = Product.query.filter(
            Product.stock > 0,
            Product.name.ilike(f"%{query}%")
        ).all()
    else:
        products = Product.query.filter(Product.stock > 0).all()

    return render_template("index.html", products=products)



@app.route('/create-admin')
def create_admin():
    admin = Admin(
        username="admin",
        password=generate_password_hash("admin123")
    )
    db.session.add(admin)
    db.session.commit()
    return "Admin Created"




@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username']).first()

        if admin and check_password_hash(admin.password, request.form['password']):
            session['admin'] = admin.username
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('invalid_login.html')
        
    return render_template('admin_login.html')




@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            price=request.form['price'],
            stock=request.form['stock'],
            image=request.form.get('image', 'default.png')
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_product.html')




@app.route("/bulk-add", methods=["POST"])
def bulk_add():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    file = request.files.get('file')

    if not file:
        return "No file uploaded"

    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)

    for row in reader:
        product = Product(
            name=row['name'],
            price=str(row['price']),
            stock=int(row['stock']),
            image=row.get('image', 'default.webp')
        )
        db.session.add(product)

    db.session.commit()
    return redirect(url_for('admin_dashboard'))




@app.route('/admin-dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    products = Product.query.all()
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template('admin_dashboard.html', products=products ,orders=orders )




@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']

        # 🔍 CHECK IF EMAIL ALREADY EXISTS
        existing_customer = Customer.query.filter_by(email=email).first()
        if existing_customer:
            return "Email already registered. Please login."

        hashed_password = generate_password_hash(request.form['password'])

        customer = Customer(
            name=request.form['name'],
            email=email,
            password=hashed_password
        )

        db.session.add(customer)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Customer.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('customer_dashboard'))
        else:
            return render_template('invalid_login.html')


    return render_template('login.html')



@app.route("/choose-login")
def func():
    return render_template('choose_login.html')


@app.route("/customer-dashboard")
def customer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('q')  # 🔍 search text
    user_id = session['user_id']

    if query:
        products = Product.query.filter(
            Product.name.ilike(f"%{query}%")
        ).all()
    else:
        products = Product.query.all()

    cart_items = Cart.query.filter_by(user_id=user_id).all()
    cart_count = sum(item.quantity for item in cart_items)

    return render_template(
    "dashboard.html",
    products=products,
    cart_items=cart_items,
    cart_count=cart_count,
    search_query=query
)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))




@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    cart_item = Cart.query.filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(
            user_id=user_id,
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)

    db.session.commit()
    return redirect(url_for('customer_dashboard'))






@app.route("/cart")
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.id.desc()).all()

    total = 0
    for item in cart_items:
        item.unit_price = fine(item.product.price)   # numeric price
        item.item_total = item.unit_price * item.quantity
        total += item.item_total

    # print(type(total))

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total= total,
        orders=orders
    )


@app.route("/place-order")
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # 1️ Get user's cart items
    cart_items = Cart.query.filter_by(user_id=user_id).all()

    if not cart_items:
        return redirect(url_for('cart'))

    # 2️ Calculate total
    total = 0
    for item in cart_items:
        total += fine(item.product.price) * item.quantity

    # 3️ Create order
    order = Order(
        user_id=user_id,
        total_amount=total
    )
    db.session.add(order)
    db.session.commit()   # to get order.id

    # 4️ Move cart → order items
    for item in cart_items:
        order_item = OrderItem(
            product_id=item.product_id,
            order_id=order.id,
            quantity=item.quantity,
            price=fine(item.product.price)
        )
        db.session.add(order_item)

    for item in cart_items:
        print(type(item.product.stock))
        curr_stock = (item.product.stock) -  item.quantity
        item.product.stock = (curr_stock)
        print(type(item.product.stock))


    # 5️Clear cart
    Cart.query.filter_by(user_id=user_id).delete()

    db.session.commit()

    return render_template("order_success.html", order_id=order.id)



@app.route("/delete-order/<int:order_id>")
def delete_order(order_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    order = Order.query.get_or_404(order_id)

    # 🔥 delete related order items first
    OrderItem.query.filter_by(order_id=order_id).delete()

    db.session.delete(order)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))





@app.route("/remove/<int:cart_id>")
def remove(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item = Cart.query.filter_by(
        id=cart_id,
        user_id=session['user_id']
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for('cart'))




@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    product = Product.query.get_or_404(product_id)

    # 🔥 Delete related cart items FIRST
    Cart.query.filter_by(product_id=product_id).delete()

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))



@app.route("/increase/<int:cart_id>")
def increase(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item = Cart.query.filter_by(
        id=cart_id,
        user_id=session['user_id']
    ).first_or_404()

    item.quantity += 1
    db.session.commit()

    return redirect(url_for('cart'))



@app.route("/decrease/<int:cart_id>")
def decrease(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item = Cart.query.filter_by(
        id=cart_id,
        user_id=session['user_id']
    ).first_or_404()

    # Decrease quantity but never below 1
    if item.quantity > 1:
        item.quantity -= 1
        db.session.commit()
    else:
        # Optional: remove item if quantity becomes 0
        db.session.delete(item)
        db.session.commit()

    return redirect(url_for('cart'))


@app.route("/routes")
def routes():
    return "<br>".join(str(rule) for rule in app.url_map.iter_rules())





if __name__ == "__main__":
    app.run()
