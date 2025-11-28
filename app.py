from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
import datetime

from config import MONGO_URI, SECRET_KEY

app = Flask(__name__)
app.config["MONGO_URI"] = MONGO_URI
app.secret_key = SECRET_KEY

mongo = PyMongo(app)
db = mongo.db

# Upload config
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- Helpers ----------
def get_cart():
    return session.setdefault('cart', {})

# ---------- Routes ----------
@app.route('/')
def index():
    categories = list(db.categories.find())
    featured = list(db.products.find().limit(8))
    return render_template('index.html', categories=categories, products=featured)

@app.route('/products')
def products():
    q = request.args.get('q', '')
    cat = request.args.get('category', '')
    query = {}
    if q:
        query['$text'] = {'$search': q}
    if cat:
        query['category'] = cat
    products = list(db.products.find(query))
    categories = list(db.categories.find())
    return render_template('products.html', products=products, categories=categories, q=q, selected_cat=cat)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = db.products.find_one({'_id': ObjectId(product_id)})
    reviews = list(db.reviews.find({'product_id': ObjectId(product_id)}))
    return render_template('product.html', product=product, reviews=reviews)

@app.route('/add-to-cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    qty = int(request.form.get('quantity', 1))
    cart = get_cart()
    if product_id in cart:
        cart[product_id] += qty
    else:
        cart[product_id] = qty
    session['cart'] = cart
    flash('Added to cart')
    return redirect(request.referrer or url_for('products'))

@app.route('/cart')
def cart():
    cart = get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        prod = db.products.find_one({'_id': ObjectId(pid)})
        if not prod:
            continue
        subtotal = prod['price'] * qty
        items.append({'product': prod, 'qty': qty, 'subtotal': subtotal})
        total += subtotal
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/update', methods=['POST'])
def update_cart():
    cart = {}
    for pid, qty in request.form.items():
        try:
            q = int(qty)
        except:
            q = 0
        if q > 0:
            cart[pid] = q
    session['cart'] = cart
    flash('Cart updated')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to place order')
        return redirect(url_for('login'))
    cart = get_cart()
    if not cart:
        flash('Cart empty')
        return redirect(url_for('cart'))

    order_items = []
    total = 0
    for pid, qty in cart.items():
        prod = db.products.find_one({'_id': ObjectId(pid)})
        if not prod:
            continue
        order_items.append({
            'product_id': prod['_id'],
            'name': prod['name'],
            'price': prod['price'],
            'quantity': qty
        })
        total += prod['price'] * qty

    order = {
        'user_id': ObjectId(session['user_id']),
        'items': order_items,
        'total': total,
        'status': 'placed',
        'created_at': datetime.datetime.utcnow()
    }
    res = db.orders.insert_one(order)
    session['cart'] = {}
    flash('Order placed successfully')
    return render_template('order_success.html', order_id=str(res.inserted_id), total=total)

# ---------- Authentication ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # hash in real apps
        if db.users.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))
        db.users.insert_one({'username': username, 'password': password, 'created_at': datetime.datetime.utcnow()})
        flash('Registered. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({'username': username, 'password': password})
        if not user:
            flash('Invalid credentials')
            return redirect(url_for('login'))
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        flash('Logged in')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('index'))

# ---------- Admin ----------
@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        flash("Access denied. Admins only.")
        return redirect(url_for('index'))

    products = list(db.products.find())
    orders = list(db.orders.find().sort('created_at', -1).limit(20))
    return render_template('admin.html', products=products, orders=orders)

@app.route('/admin/delete/<product_id>', methods=['POST'])
def admin_delete_product(product_id):
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access")
        return redirect(url_for('index'))

    db.products.delete_one({'_id': ObjectId(product_id)})
    flash("Product deleted successfully")
    return redirect(url_for('admin'))

@app.route('/admin/add-product', methods=['GET', 'POST'])
def admin_add_product():
    if 'username' not in session or session['username'] != 'admin':
        flash("Access denied. Admins only.")
        return redirect(url_for('index'))

    categories = [c['name'] for c in db.categories.find()]

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']

        images = []
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                images.append(f"/{file_path.replace(os.sep, '/')}")

        product = {
            "name": name,
            "description": description,
            "price": price,
            "stock": stock,
            "category": category,
            "images": images,
            "created_at": datetime.datetime.utcnow()
        }
        db.products.insert_one(product)
        flash("Product added successfully")
        return redirect(url_for('admin'))

    return render_template('admin_add_product.html', categories=categories)

# ---------- API ----------
@app.route('/api/products')
def api_products():
    products = list(db.products.find())
    for p in products:
        p['_id'] = str(p['_id'])
    return jsonify(products)

# ---------- Reviews ----------
@app.route('/product/<product_id>/review', methods=['POST'])
def add_review(product_id):
    if 'user_id' not in session:
        flash('Login to add review')
        return redirect(url_for('login'))
    text = request.form.get('review')
    rating = int(request.form.get('rating', 5))
    review = {
        'product_id': ObjectId(product_id),
        'user_id': ObjectId(session['user_id']),
        'username': session.get('username'),
        'rating': rating,
        'text': text,
        'created_at': datetime.datetime.utcnow()
    }
    db.reviews.insert_one(review)
    flash('Review posted')
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/cart/remove/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
    session['cart'] = cart
    return redirect(url_for('cart'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
