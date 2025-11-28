from pymongo import MongoClient, TEXT
from bson.objectid import ObjectId
import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client['ecommerce_demo']

# Clear
db.categories.drop()
db.products.drop()
db.users.drop()
db.orders.drop()
db.reviews.drop()

# Categories
cat_ids = {}
categories = [
    {"name":"Electronics","description":"Phones, laptops and accessories"},
    {"name":"Fashion","description":"Clothing and accessories"},
    {"name":"Home","description":"Home & kitchen"},
    {"name":"Books","description":"Fiction & non-fiction"},
]
for c in categories:
    res = db.categories.insert_one(c)
    cat_ids[c['name']] = res.inserted_id

# Products - using image placeholders
placeholder = "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80&auto=format&fit=crop"
products = [
    {
        "name": "Wireless Headphones",
        "description": "Noise-cancelling over-ear headphones",
        "price": 129.99,
        "stock": 30,
        "category": "Electronics",  # store name instead of ObjectId
        "images": ["/static/images/headphones.jpg"],
        "created_at": datetime.datetime.utcnow()
    },
    {
        "name": "Smartphone X",
        "description": "6.5 inch display smartphone with 128GB storage",
        "price": 699.00,
        "stock": 15,
        "category": "Electronics",
        "images": ["/static/images/smartphone.jpg"],
        "created_at": datetime.datetime.utcnow()
    },
    {
        "name": "Men's Denim Jacket",
        "description": "Classic fit denim jacket",
        "price": 59.99,
        "stock": 50,
        "category": "Fashion",
        "images": ["/static/images/denim_jacket.jpg"],
        "created_at": datetime.datetime.utcnow()
    },
    {
        "name": "Cooking Pan Set",
        "description": "Non-stick 3-piece cooking pan set",
        "price": 79.50,
        "stock": 20,
        "category": "Home",
        "images": ["/static/images/pan_set.jpg"],
        "created_at": datetime.datetime.utcnow()
    },
    {
        "name": "Learning Python (Book)",
        "description": "A modern introduction to Python.",
        "price": 39.00,
        "stock": 100,
        "category": "Books",
        "images": ["/static/images/python_book.jpg"],
        "created_at": datetime.datetime.utcnow()
    }
]


for p in products:
    db.products.insert_one(p)

# Create text index for simple search
db.products.create_index([('name', TEXT), ('description', TEXT)])

# Users
db.users.insert_one({'username': 'admin', 'password': 'adminpass', 'created_at': datetime.datetime.utcnow()})
db.users.insert_one({'username': 'user1', 'password': 'user1pass', 'created_at': datetime.datetime.utcnow()})

# Reviews
prod = db.products.find_one({})
if prod:
    db.reviews.insert_one({
        'product_id': prod['_id'],
        'user_id': db.users.find_one({'username':'user1'})['_id'],
        'username': 'user1',
        'rating': 5,
        'text': 'Excellent product, highly recommended!',
        'created_at': datetime.datetime.utcnow()
    })

print("Sample data inserted.")
