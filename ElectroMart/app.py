# ================= IMPORTS =================
from flask import Flask, render_template, request, redirect, session, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import razorpay
import time
from datetime import timedelta


import os
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================= DATABASE =================
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="electromart",
        user="postgres",
        password="Payal@123"
    )

# ================= RAZORPAY =================
razorpay_client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_SECRET"))

# ================= AUTH =================
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get('admin'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return wrap

# ================= ADMIN LOGIN =================
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM admins WHERE username=%s",
                    (request.form['username'],))
        admin = cur.fetchone()

        cur.close()
        conn.close()

        if admin and admin[2] == request.form['password']:
            session['admin'] = True
            return redirect('/admin')
        else:
            flash("Invalid admin login")

    return render_template('admin_login.html')

# ================= HOME =================
@app.route('/')
def home():
    search = request.args.get('search')
    category = request.args.get('category')

    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if search:
        query += " AND name ILIKE %s"
        params.append(f"%{search}%")

    if category:
        query += " AND category = %s"
        params.append(category)

    cur.execute(query, tuple(params))
    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('home.html', products=products)

# ================= REGISTER =================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (name,email,password)
                VALUES (%s,%s,%s)
            """, (
                request.form['name'],
                request.form['email'],
                generate_password_hash(request.form['password'])
            ))
            conn.commit()
            return redirect('/login')
        except:
            conn.rollback()
            flash("Email already exists")

        cur.close()
        conn.close()

    return render_template('register.html')

# ================= LOGIN =================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s",
                    (request.form['email'],))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[3], request.form['password']):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect('/')
        else:
            flash("Invalid credentials")

    return render_template('login.html')

# ================= FORGOT PASSWORD =================
@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s",
                    (request.form['email'],))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session['reset_email'] = request.form['email']
            return redirect('/reset-password')
        else:
            flash("Email not found")

    return render_template('forgot_password.html')

# ================= RESET PASSWORD =================
@app.route('/reset-password', methods=['GET','POST'])
def reset_password():
    if 'reset_email' not in session:
        return redirect('/forgot-password')

    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users SET password=%s WHERE email=%s
        """, (
            generate_password_hash(request.form['password']),
            session['reset_email']
        ))

        conn.commit()
        cur.close()
        conn.close()

        session.pop('reset_email')
        return redirect('/login')

    return render_template('reset_password.html')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ================= PRODUCT =================
# ================= PRODUCT DETAIL =================
@app.route('/product/<int:id>')
def product_detail(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cur.fetchone()

    cur.execute("""
        SELECT users.name, reviews.rating, reviews.review, reviews.id
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        WHERE product_id=%s
        ORDER BY reviews.id DESC
    """, (id,))
    reviews = cur.fetchall()

    cur.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id=%s", (id,))
    avg_rating, review_count = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('product_detail.html',
        product=product,
        reviews=reviews,
        avg_rating=avg_rating or 0,
        review_count=review_count
    )


@app.route('/edit_review/<int:review_id>/<int:product_id>', methods=['GET','POST'])
@login_required
def edit_review(review_id, product_id):

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        rating = request.form['rating']
        review = request.form['review']

        cur.execute("""
            UPDATE reviews
            SET rating=%s, review=%s
            WHERE id=%s
        """, (rating, review, review_id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(f'/product/{product_id}')

    cur.execute("SELECT rating, review FROM reviews WHERE id=%s", (review_id,))
    data = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('edit_review.html', data=data)   



@app.route('/delete_review/<int:review_id>/<int:product_id>')
@login_required
def delete_review(review_id, product_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM reviews WHERE id=%s", (review_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(f'/product/{product_id}')

# ================= CART =================
@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    user_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM cart WHERE user_id=%s AND product_id=%s", (user_id, id))
    item = cur.fetchone()

    if item:
        cur.execute("UPDATE cart SET quantity=quantity+1 WHERE id=%s", (item[0],))
    else:
        cur.execute("INSERT INTO cart(user_id,product_id,quantity) VALUES(%s,%s,1)",
                    (user_id, id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/cart')

@app.route('/cart')
@login_required
def cart():
    user_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT cart.id, products.name, products.price, cart.quantity, products.image
        FROM cart JOIN products ON cart.product_id=products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    items = cur.fetchall()
    total = sum(i[2]*i[3] for i in items)

    cur.close()
    conn.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/increase_qty/<int:id>')
@login_required
def increase_qty(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cart SET quantity=quantity+1 WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/cart')

@app.route('/decrease_qty/<int:id>')
@login_required
def decrease_qty(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT quantity FROM cart WHERE id=%s", (id,))
    qty = cur.fetchone()[0]

    if qty > 1:
        cur.execute("UPDATE cart SET quantity=quantity-1 WHERE id=%s", (id,))
    else:
        cur.execute("DELETE FROM cart WHERE id=%s", (id,))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/cart')

@app.route('/remove_from_cart/<int:id>')
@login_required
def remove_from_cart(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/cart')

# ================= WISHLIST =================
@app.route('/wishlist')
@login_required
def wishlist():
    user_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
SELECT p.id, p.name, p.price, p.image
FROM wishlist w
JOIN products p ON w.product_id = p.id
WHERE w.user_id=%s
""", (user_id,))

    items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('wishlist.html', items=items)

@app.route('/add_to_wishlist/<int:id>')
@login_required
def add_to_wishlist(id):
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor()

    # 🚫 Check duplicate
    cur.execute("SELECT * FROM wishlist WHERE user_id=%s AND product_id=%s", (user_id, id))
    exists = cur.fetchone()

    if exists:
        cur.close()
        conn.close()
        return "exists"

    # ✅ Insert
    cur.execute("INSERT INTO wishlist(user_id, product_id) VALUES(%s,%s)", (user_id, id))
    conn.commit()

    cur.close()
    conn.close()

    return "added"

@app.route('/remove_from_wishlist/<int:id>')
@login_required
def remove_from_wishlist(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM wishlist WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/wishlist')

# ================= RATING =================
@app.route('/add_review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    user_id = session['user_id']
    rating = request.form.get('rating')
    review = request.form.get('review')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO reviews(user_id, product_id, rating, review)
        VALUES(%s,%s,%s,%s)
    """, (user_id, product_id, rating, review))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f'/product/{product_id}')

# ================= ADDRESS =================
@app.route('/address', methods=['GET','POST'])
@login_required
def address():
    if request.method == 'POST':
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO addresses(user_id,full_name,phone,address_line,city,state,postal_code)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (
            session['user_id'],
            request.form['name'],
            request.form['phone'],
            request.form['address'],
            request.form['city'],
            request.form['state'],
            request.form['pin']
        ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect('/payment')

    return render_template('address.html')

# ================= PAYMENT =================
@app.route('/payment')
@login_required
def payment():
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT products.price, cart.quantity
        FROM cart 
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    items = cur.fetchall()

    total = sum(i[0] * i[1] for i in items)

    cur.close()
    conn.close()

    # ❗ If cart empty → go back
    if total == 0:
        return redirect('/cart')

    # ✅ ONLY show payment options page
    return render_template('payment.html', total=total)

# ================= PAYMENT METHOD =================
@app.route('/payment_method', methods=['POST'])
@login_required
def payment_method():
    method = request.form['method']

    # Save method (optional but useful)
    session['payment_method'] = method

    if method == 'cod':
        return redirect('/place_order')

    elif method == 'online':
        return redirect('/payment_gateway')
    
    # ================= PAYMENT GATEWAY =================
@app.route('/payment_gateway')
@login_required
def payment_gateway():
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT products.price, cart.quantity
        FROM cart 
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    items = cur.fetchall()
    total = sum(i[0] * i[1] for i in items)

    order = razorpay_client.order.create({
        "amount": int(total * 100),
        "currency": "INR",
        "payment_capture": "1"
    })

    cur.close()
    conn.close()

    return render_template('payment_gateway.html', order=order)
#============ PAYMENT SUCCESS ==================
@app.route('/payment_success')
@login_required
def payment_success():
    return render_template('payment_success.html')
# ================= PLACE ORDER =================
@app.route('/place_order')
@login_required
def place_order():
    user_id = session['user_id']

    conn = get_connection()
    cur = conn.cursor()

    # 🔹 Get cart items
    cur.execute("""
        SELECT product_id, quantity 
        FROM cart 
        WHERE user_id=%s
    """, (user_id,))
    cart_items = cur.fetchall()

    # ❗ If cart empty
    if not cart_items:
        return redirect('/cart')

    # 🔹 Get latest address
    cur.execute("""
        SELECT id 
        FROM addresses 
        WHERE user_id=%s 
        ORDER BY id DESC 
        LIMIT 1
    """, (user_id,))
    
    addr = cur.fetchone()

    # ❗ If no address
    if not addr:
        return redirect('/address')

    address_id = addr[0]

    # 🔹 Calculate total
    total = 0
    for item in cart_items:
        cur.execute("SELECT price FROM products WHERE id=%s", (item[0],))
        price = cur.fetchone()[0]
        total += price * item[1]

    # 🔹 Get payment method (VERY IMPORTANT)
    payment_method = session.get('payment_method', 'cod')

    # 🔹 Insert order
    cur.execute("""
        INSERT INTO orders(user_id, address_id, total_amount, payment_method)
        VALUES(%s,%s,%s,%s)
        RETURNING id
    """, (user_id, address_id, total, payment_method))

    order_id = cur.fetchone()[0]

    # 🔹 Insert order items
    for item in cart_items:
        cur.execute("SELECT price FROM products WHERE id=%s", (item[0],))
        price = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO order_items(order_id, product_id, quantity, price)
            VALUES(%s,%s,%s,%s)
        """, (order_id, item[0], item[1], price))

    # 🔹 Clear cart
    cur.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    session['last_order_id'] = order_id
    return redirect('/order_success')
#==========ORDER SUCCESS===========
@app.route('/order_success')
@login_required
def order_success():
    order_id = session.get('last_order_id')
    return render_template('order_success.html', order_id=order_id)
# ================= ORDERS =================
@app.route('/orders')
@login_required
def orders():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, total_amount, status, created_at, payment_method
        FROM orders 
        WHERE user_id=%s 
        ORDER BY id DESC
    """, (session['user_id'],))

    data = cur.fetchall()

    cur.close()
    conn.close()

    orders = []
    for o in data:
        estimated = o[3] + timedelta(days=3)

        # ✅ Now o[5] exists
        orders.append(o + (estimated,))

    return render_template('orders.html', orders=orders)

# ================= ADMIN =================
@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM orders")
    orders = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders")
    revenue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template('admin_dashboard.html',
                           total_orders=orders,
                           revenue=revenue,
                           total_products=products)
#==========ADMIN ORDERS================
@app.route('/admin/orders')
@admin_required
def admin_orders():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            orders.id,
            users.name,
            addresses.phone,
            addresses.address_line,
            products.name,
            order_items.quantity,
            orders.total_amount,
            orders.status
        FROM orders
        JOIN users ON orders.user_id = users.id
        JOIN addresses ON orders.address_id = addresses.id
        JOIN order_items ON orders.id = order_items.order_id
        JOIN products ON order_items.product_id = products.id
        ORDER BY orders.id DESC
    """)

    orders = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin_orders.html', orders=orders)

# ================= ADMIN ACTIONS =================
@app.route('/admin/accept_order/<int:id>')
@admin_required
def accept(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status='Accepted' WHERE id=%s", (id,))
    conn.commit()
    return redirect('/admin/orders')

@app.route('/admin/reject_order/<int:id>')
@admin_required
def reject(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status='Rejected' WHERE id=%s", (id,))
    conn.commit()
    return redirect('/admin/orders')

@app.route('/admin/ship_order/<int:id>')
@admin_required
def ship(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status='Shipped' WHERE id=%s", (id,))
    conn.commit()
    return redirect('/admin/orders')

@app.route('/admin/deliver_order/<int:id>')
@admin_required
def deliver(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status='Delivered' WHERE id=%s", (id,))
    conn.commit()
    return redirect('/admin/orders')

# ================= ADMIN PRODUCTS =================
@app.route('/admin/products')
@admin_required
def admin_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY id DESC")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin_products.html', products=data)

# ================= ADD PRODUCT =================
@app.route('/admin/add_product', methods=['GET','POST'])
@admin_required
def add_product():
    if request.method == 'POST':

        name = request.form.get('name')
        desc = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')   # ✅ NEW

        image_file = request.files.get('image')

        # ❌ Validation
        if not image_file or image_file.filename == "":
            flash("❌ Please select an image")
            return redirect('/admin/add_product')

        if not category:
            flash("❌ Please enter category")
            return redirect('/admin/add_product')

        # ✅ Safe filename (avoid duplicate overwrite)
        filename = secure_filename(image_file.filename)
        unique_filename = str(int(time.time())) + "_" + filename

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        image_file.save(filepath)

        # ✅ Save relative path
        image_path = f"uploads/{unique_filename}"

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products (name, description, price, image, category)
            VALUES (%s,%s,%s,%s,%s)
        """, (name, desc, price, image_path, category))

        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Product added successfully")
        return redirect('/admin/products')

    return render_template('add_product.html')

# ================= EDIT PRODUCT =================
@app.route('/admin/edit_product/<int:id>', methods=['GET','POST'])
@admin_required
def edit_product(id):
    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['description']
        price = request.form['price']

        image_file = request.files['image']

        if image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

            cur.execute("""
                UPDATE products
                SET name=%s, description=%s, price=%s, image=%s
                WHERE id=%s
            """, (name, desc, price, image_path, id))
        else:
            cur.execute("""
                UPDATE products
                SET name=%s, description=%s, price=%s
                WHERE id=%s
            """, (name, desc, price, id))

        conn.commit()
        cur.close()
        conn.close()

        flash("✏️ Product updated successfully!")

        return redirect('/admin/products')

    # GET
    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:id>')
@admin_required
def delete_product(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect('/admin/products')



# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)