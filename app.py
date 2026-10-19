from flask import Flask, render_template, request, redirect, session
import mysql.connector
import random

app = Flask(__name__)

# Session Secret Key
app.secret_key = "campusbite_secret_key"


# -----------------------------
# MySQL Database Connection
# -----------------------------
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="canteen_db"
    )
    return connection


# -----------------------------
# Home Page
# -----------------------------
@app.route("/")
def home():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM food_items")
    foods = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("index.html", foods=foods)


# -----------------------------
# Cart Page
# -----------------------------
@app.route("/cart")
def cart():
    return render_template("cart.html")


# -----------------------------
# Register Page
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            return render_template(
                "register.html",
                error="Email already registered"
            )

        query = """
        INSERT INTO users (name, email, password)
        VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (name, email, password)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/login")

    return render_template("register.html")


# -----------------------------
# Login Page
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT * FROM users
        WHERE email = %s AND password = %s
        """

        cursor.execute(
            query,
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user:

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            return redirect("/")

        else:

            return render_template(
                "login.html",
                error="Invalid email or password"
            )

    return render_template("login.html")
@app.route("/apply-coupon", methods=["POST"])
def apply_coupon():

    if "user_id" not in session:
        return {
            "success": False,
            "message": "Please login first"
        }

    data = request.get_json()

    coupon_code = data.get("coupon_code", "").strip().upper()
    cart_items = data.get("cart", [])

    if not coupon_code:
        return {
            "success": False,
            "message": "Please enter coupon code"
        }

    if not cart_items:
        return {
            "success": False,
            "message": "Cart is empty"
        }

    total_amount = 0

    for item in cart_items:
        total_amount += (
            float(item["price"]) *
            int(item["quantity"])
        )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM coupons
        WHERE code = %s
        AND status = 'Active'
    """, (coupon_code,))

    coupon = cursor.fetchone()

    cursor.close()
    connection.close()

    if not coupon:
        return {
            "success": False,
            "message": "Invalid coupon code"
        }

    if total_amount < float(coupon["min_order_amount"]):
        return {
            "success": False,
            "message": "Minimum order amount is ₹" +
                       str(coupon["min_order_amount"])
        }

    discount = (
        total_amount *
        int(coupon["discount_percent"]) /
        100
    )

    final_amount = total_amount - discount

    return {
        "success": True,
        "message": "Coupon applied successfully!",
        "coupon_code": coupon_code,
        "discount_percent": coupon["discount_percent"],
        "discount": round(discount, 2),
        "total": round(total_amount, 2),
        "final_amount": round(final_amount, 2)
    }

@app.route("/place-order", methods=["POST"])
def place_order():

    if "user_id" not in session:
        return {
            "success": False,
            "message": "Please login first"
        }

    data = request.get_json()

    cart_items = data.get("cart", [])
    coupon_code = data.get("coupon_code")
    coupon_discount = float(data.get("coupon_discount", 0))

    if not cart_items:
        return {
            "success": False,
            "message": "Cart is empty"
        }

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Calculate cart total
    total_amount = 0

    for item in cart_items:

        total_amount += (
            float(item["price"]) *
            int(item["quantity"])
        )

    # Validate coupon again on backend
    final_amount = total_amount
    actual_discount = 0

    if coupon_code:

        cursor.execute("""
            SELECT *
            FROM coupons
            WHERE code = %s
            AND status = 'Active'
        """, (coupon_code,))

        coupon = cursor.fetchone()

        if not coupon:

            cursor.close()
            connection.close()

            return {
                "success": False,
                "message": "Invalid coupon code"
            }

        # Check minimum order amount
        if total_amount < float(coupon["min_order_amount"]):

            cursor.close()
            connection.close()

            return {
                "success": False,
                "message": "Minimum order amount is ₹" +
                           str(coupon["min_order_amount"])
            }

        # Calculate actual discount
        actual_discount = (
            total_amount *
            int(coupon["discount_percent"]) /
            100
        )

        final_amount = total_amount - actual_discount

    # Generate order token
    order_token = "CB" + str(random.randint(1000, 9999))

    # Insert order
    order_query = """
    INSERT INTO orders
    (user_id, order_token, total_amount, status)
    VALUES (%s, %s, %s, %s)
    """

    cursor.execute(
        order_query,
        (
            session["user_id"],
            order_token,
            round(final_amount, 2),
            "Pending"
        )
    )

    order_id = cursor.lastrowid

    # Insert order items
    item_query = """
    INSERT INTO order_items
    (order_id, food_id, quantity, price)
    VALUES (%s, %s, %s, %s)
    """

    for item in cart_items:

        cursor.execute(
            item_query,
            (
                order_id,
                item["id"],
                item["quantity"],
                item["price"]
            )
        )

    connection.commit()

    cursor.close()
    connection.close()

    return {
        "success": True,
        "order_token": order_token,
        "total": round(final_amount, 2),
        "discount": round(actual_discount, 2)
    }

# -----------------------------
# My Orders
# -----------------------------
@app.route("/orders")
def orders():

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get user orders
    query = """
    SELECT
        id,
        order_token,
        total_amount,
        status,
        refund_status,
        refund_amount,
        order_date,
        cancelled_at
    FROM orders
    WHERE user_id = %s
    ORDER BY order_date DESC
    """

    cursor.execute(
        query,
        (session["user_id"],)
    )

    user_orders = cursor.fetchall()

    # Get food items and reviews for every order
    for order in user_orders:

        cursor.execute("""
            SELECT
                food_items.id AS food_id,
                food_items.name,
                order_items.quantity,
                order_items.price
            FROM order_items
            JOIN food_items
                ON order_items.food_id = food_items.id
            WHERE order_items.order_id = %s
        """, (order["id"],))

        order["items"] = cursor.fetchall()

        # Get reviews for this order
        cursor.execute("""
            SELECT
                reviews.food_id,
                reviews.rating,
                reviews.review,
                food_items.name
            FROM reviews
            JOIN food_items
                ON reviews.food_id = food_items.id
            WHERE reviews.order_id = %s
        """, (order["id"],))

        order["reviews"] = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "orders.html",
        orders=user_orders
    )
# -----------------------------
# Food Rating & Review
# -----------------------------
@app.route("/add-review/<int:order_id>/<int:food_id>", methods=["POST"])
def add_review(order_id, food_id):

    if "user_id" not in session:
        return redirect("/login")

    rating = request.form["rating"]
    review = request.form["review"]

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check whether user already reviewed this food for this order
    cursor.execute("""
        SELECT id
        FROM reviews
        WHERE user_id = %s
        AND food_id = %s
        AND order_id = %s
    """, (
        session["user_id"],
        food_id,
        order_id
    ))

    existing_review = cursor.fetchone()

    if existing_review:

        cursor.close()
        connection.close()

        return redirect("/orders")

    # Add review
    cursor.execute("""
        INSERT INTO reviews
        (user_id, food_id, order_id, rating, review)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        session["user_id"],
        food_id,
        order_id,
        rating,
        review
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/orders")
# -----------------------------
# Cancel Order + Refund
# -----------------------------
@app.route("/cancel-order/<int:order_id>", methods=["POST"])
def cancel_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Find user's order
    cursor.execute("""
        SELECT id, total_amount, status
        FROM orders
        WHERE id = %s AND user_id = %s
    """, (order_id, session["user_id"]))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        connection.close()
        return redirect("/orders")

    # Only Pending or Preparing orders can be cancelled
    if order["status"] not in ["Pending", "Preparing"]:
        cursor.close()
        connection.close()
        return redirect("/orders")

    # Cancel order and mark refund
    cursor.execute("""
        UPDATE orders
        SET
            status = 'Cancelled',
            refund_status = 'Refunded',
            refund_amount = total_amount,
            cancelled_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (order_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/orders")
# -----------------------------
# Customer - Order Tracking
# -----------------------------
@app.route("/track-order/<int:order_id>")
def track_order(order_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            order_token,
            total_amount,
            status,
            order_date
        FROM orders
        WHERE id = %s AND user_id = %s
    """, (order_id, session["user_id"]))

    order = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "track_order.html",
        order=order
    )


# -----------------------------
# Admin Orders
# -----------------------------
@app.route("/admin/orders")
def admin_orders():
    if "admin" not in session:
        return redirect("/admin/login")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        orders.id,
        orders.order_token,
        orders.total_amount,
        orders.status,
        orders.order_date,
        users.name,
        users.email
    FROM orders
    JOIN users ON orders.user_id = users.id
    ORDER BY orders.order_date DESC
    """

    cursor.execute(query)

    all_orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_orders.html",
        orders=all_orders
    )
# -----------------------------
# Admin - Order Details
# -----------------------------
@app.route("/admin/order/<int:order_id>")
def order_details(order_id):

    if "admin" not in session:
        return redirect("/admin/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Order information
    cursor.execute("""
        SELECT
            orders.id,
            orders.order_token,
            orders.total_amount,
            orders.status,
            orders.order_date,
            users.name,
            users.email
        FROM orders
        JOIN users ON orders.user_id = users.id
        WHERE orders.id = %s
    """, (order_id,))

    order = cursor.fetchone()

    # Food items in this order
    cursor.execute("""
        SELECT
            food_items.name,
            order_items.quantity,
            order_items.price,
            (order_items.quantity * order_items.price) AS item_total
        FROM order_items
        JOIN food_items
            ON order_items.food_id = food_items.id
        WHERE order_items.order_id = %s
    """, (order_id,))

    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )

# -----------------------------
# Update Order Status
# -----------------------------
@app.route("/admin/update-status/<int:order_id>", methods=["POST"])
def update_status(order_id):

    status = request.form["status"]

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
    UPDATE orders
    SET status = %s
    WHERE id = %s
    """

    cursor.execute(
        query,
        (status, order_id)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/admin/orders")
# -----------------------------
# Admin - Add Food
# -----------------------------
# -----------------------------
# Admin - Add Food
# -----------------------------
@app.route("/admin/add-food", methods=["GET", "POST"])
def add_food():
    if "admin" not in session:
        return redirect("/admin/login")
    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        category = request.form["category"]
        icon = request.form["icon"]

        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO food_items
        (name, description, price, category, icon)
        VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                name,
                description,
                price,
                category,
                icon
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/admin/foods")

    return render_template("add_food.html")
# -----------------------------
# Admin - Edit Food
# -----------------------------
@app.route("/admin/edit-food/<int:food_id>", methods=["GET", "POST"])
def edit_food(food_id):

    if "admin" not in session:
        return redirect("/admin/login")

    # existing code...

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        category = request.form["category"]
        icon = request.form["icon"]

        query = """
        UPDATE food_items
        SET
            name = %s,
            description = %s,
            price = %s,
            category = %s,
            icon = %s
        WHERE id = %s
        """

        cursor.execute(
            query,
            (
                name,
                description,
                price,
                category,
                icon,
                food_id
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect("/admin/foods")

    cursor.execute(
        "SELECT * FROM food_items WHERE id = %s",
        (food_id,)
    )

    food = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "edit_food.html",
        food=food
    )
# -----------------------------
# Admin - Delete Food
# -----------------------------
@app.route("/admin/delete-food/<int:food_id>")
def delete_food(food_id):

    if "admin" not in session:
        return redirect("/admin/login")

    # existing code...
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM food_items WHERE id = %s",
        (food_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect("/admin/foods")
# -----------------------------
# Admin - Food List
# -----------------------------
@app.route("/admin/foods")
def admin_foods():
    if "admin" not in session:
        return redirect("/admin/login")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM food_items
        ORDER BY id DESC
    """)

    foods = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_foods.html",
        foods=foods
    )
# -----------------------------
# Admin Login
# -----------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin"] = True

            return redirect("/admin")

        else:

            return render_template(
                "admin_login.html",
                error="Invalid admin username or password"
            )

    return render_template("admin_login.html")
# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route("/admin")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin/login")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total Users
    cursor.execute(
        "SELECT COUNT(*) AS total_users FROM users"
    )
    total_users = cursor.fetchone()["total_users"]

    # Total Food Items
    cursor.execute(
        "SELECT COUNT(*) AS total_foods FROM food_items"
    )
    total_foods = cursor.fetchone()["total_foods"]

    # Total Orders
    cursor.execute(
        "SELECT COUNT(*) AS total_orders FROM orders"
    )
    total_orders = cursor.fetchone()["total_orders"]

    # Pending Orders
    cursor.execute("""
        SELECT COUNT(*) AS pending_orders
        FROM orders
        WHERE status = 'Pending'
    """)
    pending_orders = cursor.fetchone()["pending_orders"]
        # Preparing Orders
    cursor.execute("""
        SELECT COUNT(*) AS preparing_orders
        FROM orders
        WHERE status = 'Preparing'
    """)
    preparing_orders = cursor.fetchone()["preparing_orders"]


    # Ready Orders
    cursor.execute("""
        SELECT COUNT(*) AS ready_orders
        FROM orders
        WHERE status = 'Ready'
    """)
    ready_orders = cursor.fetchone()["ready_orders"]


    # Delivered Orders
    cursor.execute("""
        SELECT COUNT(*) AS delivered_orders
        FROM orders
        WHERE status = 'Delivered'
    """)
    delivered_orders = cursor.fetchone()["delivered_orders"]


    # Cancelled Orders
    cursor.execute("""
        SELECT COUNT(*) AS cancelled_orders
        FROM orders
        WHERE status = 'Cancelled'
    """)
    cancelled_orders = cursor.fetchone()["cancelled_orders"]


    # Most Ordered Food
    cursor.execute("""
        SELECT
            food_items.name,
            SUM(order_items.quantity) AS total_quantity
        FROM order_items
        JOIN food_items
            ON order_items.food_id = food_items.id
        JOIN orders
            ON order_items.order_id = orders.id
        WHERE orders.status != 'Cancelled'
        GROUP BY food_items.id, food_items.name
        ORDER BY total_quantity DESC
        LIMIT 1
    """)

    most_ordered_food = cursor.fetchone()

    # Total Sales
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total_sales
        FROM orders
    """)
    total_sales = cursor.fetchone()["total_sales"]

    # Recent Orders
    cursor.execute("""
        SELECT
            orders.id,
            orders.order_token,
            orders.total_amount,
            orders.status,
            orders.order_date,
            users.name
        FROM orders
        JOIN users
            ON orders.user_id = users.id
        ORDER BY orders.order_date DESC
        LIMIT 5
    """)

    recent_orders = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
    "admin_dashboard.html",
    total_users=total_users,
    total_foods=total_foods,
    total_orders=total_orders,
    pending_orders=pending_orders,
    preparing_orders=preparing_orders,
    ready_orders=ready_orders,
    delivered_orders=delivered_orders,
    cancelled_orders=cancelled_orders,
    total_sales=total_sales,
    most_ordered_food=most_ordered_food,
    recent_orders=recent_orders
)
# -----------------------------
# Admin Logout
# -----------------------------
@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect("/admin/login")
# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -----------------------------
# Start Flask
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)