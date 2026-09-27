// ================= CART =================

// Get cart count element
let cartCountEl = document.getElementById("cart-count");

// Get cart count from localStorage
let cartCount = parseInt(localStorage.getItem("cartCount")) || 0;

// Update cart UI
function updateCartCount() {
  if (cartCountEl) {
    cartCountEl.textContent = cartCount;
  }
}

// Add to cart
function addToCart(productName = "Product") {
  let isLoggedIn = localStorage.getItem("isLoggedIn");

  if (!isLoggedIn) {
    window.location.href = "login.html";
    return;
  }

  cartCount++;
  localStorage.setItem("cartCount", cartCount);
  updateCartCount();

  alert(productName + " added to cart 🛒");
}

// ================= WISHLIST =================

// Get wishlist from localStorage
let wishlist = JSON.parse(localStorage.getItem("wishlist")) || [];

// Update wishlist count
function updateWishlistCount() {
  let wishlistCountEl = document.getElementById("wishlist-count");
  if (wishlistCountEl) {
    wishlistCountEl.textContent = wishlist.length;
  }
}

// Add to wishlist
function addToWishlist(name, price) {
  let exists = wishlist.find(item => item.name === name);

  if (exists) {
    alert("Already in wishlist ❤️");
    return;
  }

  wishlist.push({ name, price });
  localStorage.setItem("wishlist", JSON.stringify(wishlist));

  updateWishlistCount();
  alert(name + " added to wishlist ❤️");
}

// Remove from wishlist
function removeFromWishlist(index) {
  wishlist.splice(index, 1);
  localStorage.setItem("wishlist", JSON.stringify(wishlist));

  loadWishlist();
  updateWishlistCount();
}

// Move to Cart from Wishlist
function moveToCart(index) {
  let item = wishlist[index];

  addToCart(item.name); // add to cart
  removeFromWishlist(index); // remove from wishlist
}

// Clear entire wishlist
function clearWishlist() {
  if (wishlist.length === 0) {
    alert("Wishlist already empty 😢");
    return;
  }

  if (confirm("Are you sure you want to clear wishlist?")) {
    wishlist = [];
    localStorage.setItem("wishlist", JSON.stringify(wishlist));

    loadWishlist();
    updateWishlistCount();
  }
}

// Load wishlist items
function loadWishlist() {
  let container = document.getElementById("wishlist-items");
  if (!container) return;

  container.innerHTML = "";

  if (wishlist.length === 0) {
    container.innerHTML = "<h3>Your wishlist is empty 😢</h3>";
    return;
  }

  wishlist.forEach((item, index) => {
    container.innerHTML += `
      <div class="card">
        <h3>${item.name}</h3>
        <p>Price: ₹${item.price}</p>

        <button onclick="moveToCart(${index})">🛒 Move to Cart</button>
        <button onclick="removeFromWishlist(${index})">❌ Remove</button>
      </div>
    `;
  });

  // Add Clear Wishlist button
  container.innerHTML += `
    <br>
    <button onclick="clearWishlist()" style="background:black;">
      🗑️ Clear Wishlist
    </button>
  `;
}


// ================= INIT =================
updateCartCount();
updateWishlistCount();
loadWishlist();