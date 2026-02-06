import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Star, ShoppingCart, Eye } from "lucide-react";

// Sample product data
const SAMPLE_PRODUCTS = [
  {
    id: 1,
    name: "Vitamin C Serum",
    price: 2499,
    category: "Serum",
    rating: 4.5,
    image: "https://via.placeholder.com/300x300/3b82f6/ffffff?text=Vitamin+C",
    description: "Brightening serum with 20% Vitamin C"
  },
  {
    id: 2,
    name: "Hyaluronic Acid Moisturizer",
    price: 1899,
    category: "Moisturizer",
    rating: 4.8,
    image: "https://via.placeholder.com/300x300/10b981/ffffff?text=HA+Cream",
    description: "Deep hydration with hyaluronic acid"
  },
  {
    id: 3,
    name: "Retinol Night Cream",
    price: 3299,
    category: "Night Cream",
    rating: 4.7,
    image: "https://via.placeholder.com/300x300/8b5cf6/ffffff?text=Retinol",
    description: "Anti-aging night treatment"
  },
  {
    id: 4,
    name: "Niacinamide Face Wash",
    price: 899,
    category: "Cleanser",
    rating: 4.3,
    image: "https://via.placeholder.com/300x300/f59e0b/ffffff?text=Cleanser",
    description: "Gentle cleanser for all skin types"
  },
  {
    id: 5,
    name: "SPF 50 Sunscreen",
    price: 1499,
    category: "Sunscreen",
    rating: 4.6,
    image: "https://via.placeholder.com/300x300/ef4444/ffffff?text=SPF+50",
    description: "Broad spectrum sun protection"
  },
  {
    id: 6,
    name: "AHA/BHA Exfoliant",
    price: 1999,
    category: "Exfoliant",
    rating: 4.4,
    image: "https://via.placeholder.com/300x300/06b6d4/ffffff?text=Exfoliant",
    description: "Gentle chemical exfoliation"
  },
  {
    id: 7,
    name: "Green Tea Toner",
    price: 1299,
    category: "Toner",
    rating: 4.5,
    image: "https://via.placeholder.com/300x300/84cc16/ffffff?text=Toner",
    description: "Refreshing antioxidant toner"
  },
  {
    id: 8,
    name: "Ceramide Repair Cream",
    price: 2799,
    category: "Moisturizer",
    rating: 4.9,
    image: "https://via.placeholder.com/300x300/a855f7/ffffff?text=Ceramide",
    description: "Barrier repair and moisture lock"
  }
];

export default function Marketplace() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [cart, setCart] = useState([]);

  // Filter products based on search query
  const filteredProducts = SAMPLE_PRODUCTS.filter(product => 
    product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    product.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddToCart = (product) => {
    // Check if product already exists in cart
    const existingItem = cart.find(item => item.id === product.id);
    if (!existingItem) {
      setCart([...cart, product]);
    }
    // Could show a toast notification here
  };

  const handleBuyNow = (product) => {
    // Navigate to checkout with product
    navigate('/checkout', { state: { products: [product] } });
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Header Section */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 dark:from-blue-700 dark:to-indigo-800 py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-4xl font-black text-white mb-3 tracking-tight">Skincare Marketplace</h1>
          <p className="text-blue-100 dark:text-blue-200 font-medium text-lg">
            Discover dermatologist-approved products for your skin
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Search Bar */}
        <div className="mb-8">
          <div className="relative max-w-xl">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-slate-500" size={20} />
            <input
              type="text"
              placeholder="Search products by name or category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Product Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredProducts.map(product => (
            <ProductCard 
              key={product.id}
              product={product}
              onAddToCart={handleAddToCart}
              onBuyNow={handleBuyNow}
            />
          ))}
        </div>

        {/* No Results */}
        {filteredProducts.length === 0 && (
          <div className="text-center py-20">
            <p className="text-slate-500 dark:text-slate-400 text-lg font-medium">
              No products found matching "{searchQuery}"
            </p>
          </div>
        )}

        {/* Cart Summary (if items in cart) */}
        {cart.length > 0 && (
          <div className="fixed bottom-6 right-6 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-4 border border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-3">
              <ShoppingCart className="text-blue-600 dark:text-blue-400" size={24} />
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {cart.length} {cart.length === 1 ? 'item' : 'items'} in cart
                </p>
                <button 
                  onClick={() => navigate('/checkout', { state: { products: cart } })}
                  className="text-blue-600 dark:text-blue-400 text-xs font-bold hover:underline"
                >
                  View Cart & Checkout
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ProductCard({ product, onAddToCart, onBuyNow }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden hover:shadow-xl transition-all duration-300 hover:-translate-y-1 group">
      {/* Product Image */}
      <div className="relative h-48 bg-slate-100 dark:bg-slate-700 overflow-hidden">
        <img 
          src={product.image} 
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-3 right-3 bg-white dark:bg-slate-800 px-2 py-1 rounded-lg flex items-center gap-1">
          <Star size={14} className="text-yellow-500 fill-yellow-500" />
          <span className="text-xs font-bold text-slate-900 dark:text-slate-100">{product.rating}</span>
        </div>
      </div>

      {/* Product Info */}
      <div className="p-5">
        <div className="mb-3">
          <span className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
            {product.category}
          </span>
          <h3 className="text-lg font-black text-slate-900 dark:text-slate-100 mt-1 mb-2">
            {product.name}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2">
            {product.description}
          </p>
        </div>

        <div className="flex items-center justify-between mb-4">
          <span className="text-2xl font-black text-slate-900 dark:text-slate-100">
            Rs. {product.price.toLocaleString()}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => onAddToCart(product)}
            className="flex-1 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 px-4 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2"
          >
            <ShoppingCart size={16} />
            Add
          </button>
          <button
            onClick={() => onBuyNow(product)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-xl font-bold text-sm transition-all"
          >
            Buy Now
          </button>
        </div>
      </div>
    </div>
  );
}
