import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { CreditCard, Smartphone, Banknote, MapPin, Phone, Mail, User, CheckCircle } from "lucide-react";

export default function Checkout() {
  const location = useLocation();
  const navigate = useNavigate();
  const products = location.state?.products || [];
  
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    address: "",
    city: "",
    postalCode: "",
    paymentMethod: "credit-card"
  });

  const [showConfirmation, setShowConfirmation] = useState(false);

  const totalAmount = products.reduce((sum, product) => sum + product.price, 0);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowConfirmation(true);
  };

  if (showConfirmation) {
    return <ConfirmationPage formData={formData} products={products} totalAmount={totalAmount} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12 px-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="text-blue-600 dark:text-blue-400 hover:underline mb-4 font-medium"
          >
            ← Back to Marketplace
          </button>
          <h1 className="text-4xl font-black text-slate-900 dark:text-slate-100 mb-3">Checkout</h1>
          <p className="text-slate-600 dark:text-slate-400">Complete your purchase</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Checkout Form */}
          <div className="lg:col-span-2">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Billing Information */}
              <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                <h2 className="text-xl font-black text-slate-900 dark:text-slate-100 mb-6 flex items-center gap-2">
                  <User size={20} />
                  Billing Information
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      name="fullName"
                      value={formData.fullName}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="John Doe"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                        Email *
                      </label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="john@example.com"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                        Phone *
                      </label>
                      <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="+92 300 1234567"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                      Street Address *
                    </label>
                    <input
                      type="text"
                      name="address"
                      value={formData.address}
                      onChange={handleInputChange}
                      required
                      className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="123 Main Street"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                        City *
                      </label>
                      <input
                        type="text"
                        name="city"
                        value={formData.city}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Lahore"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">
                        Postal Code *
                      </label>
                      <input
                        type="text"
                        name="postalCode"
                        value={formData.postalCode}
                        onChange={handleInputChange}
                        required
                        className="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="54000"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Payment Method */}
              <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
                <h2 className="text-xl font-black text-slate-900 dark:text-slate-100 mb-6">
                  Payment Method
                </h2>

                <div className="space-y-3">
                  <PaymentOption
                    id="credit-card"
                    name="paymentMethod"
                    value="credit-card"
                    checked={formData.paymentMethod === "credit-card"}
                    onChange={handleInputChange}
                    icon={<CreditCard size={20} />}
                    title="Credit/Debit Card"
                    description="Pay securely with your card"
                  />

                  <PaymentOption
                    id="easypaisa"
                    name="paymentMethod"
                    value="easypaisa"
                    checked={formData.paymentMethod === "easypaisa"}
                    onChange={handleInputChange}
                    icon={<Smartphone size={20} />}
                    title="EasyPaisa"
                    description="Mobile wallet payment"
                  />

                  <PaymentOption
                    id="cod"
                    name="paymentMethod"
                    value="cod"
                    checked={formData.paymentMethod === "cod"}
                    onChange={handleInputChange}
                    icon={<Banknote size={20} />}
                    title="Cash on Delivery"
                    description="Pay when you receive"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-black text-lg transition-all hover:scale-[1.02] active:scale-95"
              >
                Complete Order - Rs. {totalAmount.toLocaleString()}
              </button>
            </form>
          </div>

          {/* Order Summary */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 sticky top-6">
              <h2 className="text-xl font-black text-slate-900 dark:text-slate-100 mb-6">Order Summary</h2>

              <div className="space-y-4 mb-6">
                {products.map((product, index) => (
                  <div key={index} className="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700 last:border-0">
                    <img src={product.image} alt={product.name} className="w-16 h-16 rounded-lg object-cover" />
                    <div className="flex-1">
                      <h4 className="font-bold text-slate-900 dark:text-slate-100 text-sm">{product.name}</h4>
                      <p className="text-slate-500 dark:text-slate-400 text-xs">{product.category}</p>
                    </div>
                    <span className="font-black text-slate-900 dark:text-slate-100">
                      Rs. {product.price.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>

              <div className="border-t border-slate-200 dark:border-slate-700 pt-4 space-y-2">
                <div className="flex justify-between text-slate-600 dark:text-slate-400">
                  <span>Subtotal</span>
                  <span>Rs. {totalAmount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-slate-600 dark:text-slate-400">
                  <span>Shipping</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-bold">FREE</span>
                </div>
                <div className="flex justify-between text-xl font-black text-slate-900 dark:text-slate-100 pt-2 border-t border-slate-200 dark:border-slate-700">
                  <span>Total</span>
                  <span>Rs. {totalAmount.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PaymentOption({ id, name, value, checked, onChange, icon, title, description }) {
  return (
    <label 
      htmlFor={id}
      className={`flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition-all ${
        checked 
          ? 'border-blue-600 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
      }`}
    >
      <input
        type="radio"
        id={id}
        name={name}
        value={value}
        checked={checked}
        onChange={onChange}
        className="w-5 h-5 text-blue-600 focus:ring-2 focus:ring-blue-500"
      />
      <div className={`${checked ? 'text-blue-600 dark:text-blue-400' : 'text-slate-500 dark:text-slate-400'}`}>
        {icon}
      </div>
      <div className="flex-1">
        <h4 className={`font-bold ${checked ? 'text-blue-900 dark:text-blue-100' : 'text-slate-900 dark:text-slate-100'}`}>
          {title}
        </h4>
        <p className="text-sm text-slate-500 dark:text-slate-400">{description}</p>
      </div>
    </label>
  );
}

function ConfirmationPage({ formData, products, totalAmount }) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-12 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Success Message */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 border border-slate-200 dark:border-slate-700 text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900/20 rounded-full mb-6">
            <CheckCircle size={40} className="text-green-600 dark:text-green-400" />
          </div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-slate-100 mb-3">Order Confirmed!</h1>
          <p className="text-slate-600 dark:text-slate-400 text-lg mb-6">
            Thank you for your purchase. Your order has been successfully placed.
          </p>
          <div className="inline-block bg-slate-100 dark:bg-slate-700 px-6 py-3 rounded-xl">
            <p className="text-sm text-slate-600 dark:text-slate-400">Order Number</p>
            <p className="text-2xl font-black text-slate-900 dark:text-slate-100">
              #SKY{Math.floor(Math.random() * 100000)}
            </p>
          </div>
        </div>

        {/* Order Details */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-black text-slate-900 dark:text-slate-100 mb-4">Delivery Address</h3>
            <div className="space-y-2 text-slate-600 dark:text-slate-400">
              <p className="font-bold text-slate-900 dark:text-slate-100">{formData.fullName}</p>
              <p>{formData.address}</p>
              <p>{formData.city}, {formData.postalCode}</p>
              <p>{formData.phone}</p>
              <p>{formData.email}</p>
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700">
            <h3 className="text-lg font-black text-slate-900 dark:text-slate-100 mb-4">Order Summary</h3>
            <div className="space-y-3 mb-4">
              {products.map((product, index) => (
                <div key={index} className="flex justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">{product.name}</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">
                    Rs. {product.price.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
            <div className="border-t border-slate-200 dark:border-slate-700 pt-3">
              <div className="flex justify-between text-xl font-black text-slate-900 dark:text-slate-100">
                <span>Total Paid</span>
                <span>Rs. {totalAmount.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Delivery Location Map */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 mb-8">
          <h3 className="text-lg font-black text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
            <MapPin size={20} />
            Delivery Location
          </h3>
          <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700">
            <iframe
              title="Delivery Location"
              src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3402.6815193244893!2d74.35874731511622!3d31.47470888136949!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x391906964a8a3c45%3A0x5c9b7c1c8e8e8c8e!2sLahore%2C%20Pakistan!5e0!3m2!1sen!2s!4v1234567890123!5m2!1sen!2s"
              width="100%"
              height="350"
              style={{ border: 0 }}
              allowFullScreen=""
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            ></iframe>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-3 text-center">
            Your order will be delivered to the address shown above
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/marketplace')}
            className="flex-1 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 py-4 rounded-2xl font-bold text-lg transition-all"
          >
            Continue Shopping
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold text-lg transition-all"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
