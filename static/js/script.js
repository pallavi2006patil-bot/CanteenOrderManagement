// Get cart from browser storage
let cart = JSON.parse(localStorage.getItem("canteenCart")) || [];


// Save cart
function saveCart() {

    localStorage.setItem(
        "canteenCart",
        JSON.stringify(cart)
    );

}


function addToCart(id, name, price, image) {

    let cart = JSON.parse(localStorage.getItem("canteenCart")) || [];

    let existingItem = cart.find(item => item.id == id);

    if (existingItem) {

        existingItem.quantity++;

        // image bhi update karo
        existingItem.image = image;

    } else {

        cart.push({
            id: id,
            name: name,
            price: price,
            image: image,
            quantity: 1
        });

    }

    localStorage.setItem(
        "canteenCart",
        JSON.stringify(cart)
    );

    updateCartCount();

    alert(name + " added to cart!");

}

// Update cart count
function updateCartCount() {

    let countElement =
        document.getElementById("cart-count");


    if (!countElement) {

        return;

    }


    let totalQuantity = 0;


    cart.forEach(item => {

        totalQuantity += item.quantity;

    });


    countElement.innerText =
        totalQuantity;

}


// Display cart
function displayCart() {

    let cartContainer =
        document.getElementById("cart-items");


    if (!cartContainer) {

        return;

    }


    cartContainer.innerHTML = "";


    if (cart.length === 0) {

        cartContainer.innerHTML = `

            <div class="empty-cart">

                <div class="empty-icon">
                    🛒
                </div>

                <h2>
                    Your cart is empty
                </h2>

                <p>
                    Add some delicious food!
                </p>

                <a href="/">
                    Browse Menu
                </a>

            </div>

        `;


        updateSummary();

        return;

    }


    cart.forEach((item, index) => {

        let itemTotal =
            item.price * item.quantity;


        cartContainer.innerHTML += `

            <div class="cart-item">

                <div class="cart-food-icon">
                 <img
        src="/static/images/${item.name.toLowerCase().replaceAll(' ', '-')}.jpg"
        alt="${item.name}"
        style="width: 100px; height: 100px; object-fit: cover; border-radius: 10px;"
    >
                </div>


                <div class="cart-item-info">

                    <h3>
                        ${item.name}
                    </h3>

                    <p>
                        ₹${item.price} per item
                    </p>

                </div>


                <div class="quantity-control">

                    <button
                        onclick="decreaseQuantity(${index})">

                        −

                    </button>


                    <span>
                        ${item.quantity}
                    </span>


                    <button
                        onclick="increaseQuantity(${index})">

                        +

                    </button>

                </div>


                <div class="item-total">

                    ₹${itemTotal}

                </div>


                <button
                    class="remove-btn"
                    onclick="removeItem(${index})">

                    ✕

                </button>

            </div>

        `;

    });


    updateSummary();

}


// Increase quantity
function increaseQuantity(index) {

    cart[index].quantity++;

    saveCart();

    displayCart();

    updateCartCount();

}


// Decrease quantity
function decreaseQuantity(index) {

    if (cart[index].quantity > 1) {

        cart[index].quantity--;

    }

    else {

        cart.splice(index, 1);

    }


    saveCart();

    displayCart();

    updateCartCount();

}


// Remove item
function removeItem(index) {

    cart.splice(index, 1);

    saveCart();

    displayCart();

    updateCartCount();

}


// Update summary
function updateSummary() {

    let totalItems = 0;

    let totalPrice = 0;


    cart.forEach(item => {

        totalItems += item.quantity;

        totalPrice +=
            item.price * item.quantity;

    });


    let itemsElement =
        document.getElementById("total-items");

    let priceElement =
        document.getElementById("total-price");


    if (itemsElement) {

        itemsElement.innerText =
            totalItems;

    }


    if (priceElement) {

        priceElement.innerText =
            totalPrice;

    }

}


// Place order
function placeOrder() {

    if (cart.length === 0) {

        alert(
            "Your cart is empty!"
        );

        return;

    }


    fetch("/place-order", {

        method: "POST",

        headers: {

            "Content-Type":
                "application/json"

        },

        body: JSON.stringify({

            cart: cart

        })

    })


    .then(response => response.json())


    .then(data => {

        if (data.success) {

            alert(
                "Order placed successfully! 🎉\n\n" +
                "Order Token: " +
                data.order_token +
                "\n" +
                "Total Amount: ₹" +
                data.total
            );


            localStorage.removeItem(
                "canteenCart"
            );


            cart = [];


            displayCart();

            updateCartCount();

        }

        else {

            alert(
                data.message
            );

        }

    })


    .catch(error => {

        console.error(error);

        alert(
            "Something went wrong while placing the order."
        );

    });

}


// Run when page loads
document.addEventListener(
    "DOMContentLoaded",
    function () {

        updateCartCount();

        displayCart();


        // Add to Cart buttons
        let buttons =
            document.querySelectorAll(".add-cart-btn");


        buttons.forEach(function(button) {

            button.addEventListener(
                "click",
                function() {

                    let id =
                        Number(button.dataset.id);

                    let name =
                        button.dataset.name;

                    let price =
                        Number(button.dataset.price);
                    let image = 
                        button.dataset.image;

                    addToCart(
                        id,
                        name,
                        price
                    );

                }
            );

        });

    }
);
// -----------------------------
// Search + Category Filter
// -----------------------------

let currentCategory = "All";


function filterMenu() {

    const searchInput =
        document.getElementById("menuSearch");

    const searchText = searchInput
        ? searchInput.value.toLowerCase().trim()
        : "";

    const cards =
        document.querySelectorAll(".menu-card");


    cards.forEach(function(card) {

        const nameElement =
            card.querySelector("h3");

        const descriptionElement =
            card.querySelector("p");


        const name = nameElement
            ? nameElement.textContent.toLowerCase()
            : "";


        const description = descriptionElement
            ? descriptionElement.textContent.toLowerCase()
            : "";


        const category =
            card.getAttribute("data-category");


        const matchesSearch =
            name.includes(searchText) ||
            description.includes(searchText);


        const matchesCategory =
            currentCategory === "All" ||
            category === currentCategory;


        if (matchesSearch && matchesCategory) {

            card.style.display = "block";

        } else {

            card.style.display = "none";

        }

    });

}


function filterCategory(category) {

    currentCategory = category;

    filterMenu();


    const menuSection =
        document.getElementById("menu");


    if (menuSection) {

        menuSection.scrollIntoView({
            behavior: "smooth"
        });

    }

}


function showAllFoods() {

    // Category filter remove
    currentCategory = "All";

    // Search box clear
    const searchInput = document.getElementById("menuSearch");

    if (searchInput) {
        searchInput.value = "";
    }

    // Show all food cards
    const cards = document.querySelectorAll(".menu-card");

    cards.forEach(function(card) {
        card.style.display = "block";
    });

}