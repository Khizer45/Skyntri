import { publishCartCount } from './cartEvents.js'

// ---------------------------------------------------------------------------
// Skyntri API service layer
// ---------------------------------------------------------------------------

export const API_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/+$/, '')

const TOKEN_KEY = 'skyntri-token'

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

export function getAuthToken() {
  return getStoredToken()
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function assetUrl(path) {
  if (!path) return ''

  if (/^https?:\/\//i.test(path)) {
    return path
  }

  return `${API_URL}${path.startsWith('/') ? path : `/${path}`}`
}

// ---------------------------------------------------------------------------
// Response handling
// ---------------------------------------------------------------------------

async function parseResponse(response) {
  // HTTP 204 means "No Content".
  // There is no JSON body to parse.
  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''

  // JSON response
  if (contentType.includes('application/json')) {
    const text = await response.text()

    // Prevent "Unexpected end of JSON input"
    // when a server returns an empty body.
    if (!text.trim()) {
      return null
    }

    try {
      return JSON.parse(text)
    } catch {
      return text
    }
  }

  // Non-JSON response
  return response.text()
}

async function request(path, options = {}) {
  const token = getStoredToken()

  const headers = {
    ...(options.body instanceof FormData
      ? {}
      : { 'Content-Type': 'application/json' }),
    ...(options.headers || {}),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  const data = await parseResponse(response)

  if (!response.ok) {
    let message = 'Request failed.'

    let code = null
    let guidance = []

    if (typeof data === 'object' && data !== null) {
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (
        data.detail &&
        typeof data.detail === 'object' &&
        !Array.isArray(data.detail)
      ) {
        // Structured errors, e.g. analysis abstentions:
        // { code, status, message, guidance }
        message = data.detail.message || message
        code = data.detail.code || null
        guidance = Array.isArray(data.detail.guidance)
          ? data.detail.guidance
          : []
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((item) => item.msg || 'Invalid request.')
          .join(', ')
      } else if (typeof data.message === 'string') {
        message = data.message
      }
    } else if (typeof data === 'string' && data.trim()) {
      message = data
    }

    if (response.status === 401 && token) {
      // Expired or revoked session: drop the stored token.
      clearAuthToken()
    }

    const error = new Error(message)

    error.status = response.status
    error.data = data
    error.code = code
    error.guidance = guidance

    throw error
  }

  return data
}

// ---------------------------------------------------------------------------
// Response adapters
//
// Keep the UI contract stable while the backend remains clean/snake_case.
// ---------------------------------------------------------------------------

function mapUser(user) {
  if (!user) return null

  return {
    ...user,
    fullName: user.full_name,
    skinType: user.skin_type,
    avatarUrl: assetUrl(user.avatar_url),

    memberSince: user.created_at
      ? new Date(user.created_at).toLocaleDateString()
      : '',

    notifyAnalysis: user.notify_analysis,
    notifyReports: user.notify_reports,
  }
}

function mapAnalysis(data) {
  const conditions = Array.isArray(data?.conditions)
    ? data.conditions
    : []

  const recommendations = data?.recommendations || {}
  const confidence = data?.confidence_score ?? null

  return {
    ...data,

    imageUrl: assetUrl(data?.image_url),
    analysisId: data?.analysis_id,

    conditions,

    confidence,

    severity: data?.severity_level || 'Low',

    disclaimer: data?.disclaimer || '',

    referral: Boolean(data?.referral),
    summary: data?.summary || '',
    track: data?.analysis_track || 'facial_concerns',
    trackLabel: data?.analysis_track_label || 'Facial skin concerns',
    modelVersion: data?.model_version || '',

    explanation: data?.summary
      ? data.summary
      : conditions.length
        ? `The analysis identified these visible skin patterns: ${conditions.join(', ')}.`
        : 'No specific visible skin problem was identified from this image.',

    recommendations: {
      skincare: Array.isArray(recommendations.skincare)
        ? recommendations.skincare
        : [],

      ingredients: Array.isArray(recommendations.ingredients)
        ? recommendations.ingredients
        : [],

      sun_protection: Array.isArray(recommendations.sun_protection)
        ? recommendations.sun_protection
        : [],

      lifestyle: Array.isArray(recommendations.lifestyle)
        ? recommendations.lifestyle
        : [],

      avoid: Array.isArray(recommendations.avoid)
        ? recommendations.avoid
        : [],
    },
  }
}

function mapScan(data) {
  const ingredients = Array.isArray(data?.matched_ingredients)
    ? data.matched_ingredients
    : []

  return {
    ...data,

    imageUrl: assetUrl(data?.image_url),

    summary: {
      total: data?.total_ingredients ?? ingredients.length,
      beneficial: data?.beneficial_count ?? 0,
      caution: data?.caution_count ?? 0,
    },

    ingredients: ingredients.map((item) => ({
      ...item,

      note:
        item.personalized_warning ||
        item.precautions ||
        (
          item.safety_status === 'Beneficial'
            ? 'Generally considered beneficial based on the Skyntri ingredient database.'
            : 'Review this ingredient with care for your skin type and routine.'
        ),

      status: item.safety_status || 'Caution',
    })),

    unmatched: data?.unmatched_ingredients || [],
  }
}

function mapProgress(data) {
  return {
    ...data,

    beforeImageUrl: assetUrl(data?.before_image_url),
    afterImageUrl: assetUrl(data?.after_image_url),

    timeline: [
      {
        id: data?.id || 'current',

        label: data?.created_at
          ? new Date(data.created_at).toLocaleDateString()
          : 'Current',

        score: Number(data?.score || 0),
      },
    ],
  }
}

function mapHistory(data) {
  return (
    data || {
      analyses: [],
      scans: [],
      progress: [],
      reports: [],
    }
  )
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function loginUser(email, password) {
  if (!email || !password) {
    throw new Error('Email and password are required.')
  }

  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
    }),
  })

  if (data?.access_token) {
    setAuthToken(data.access_token)
  }

  return {
    user: mapUser(data?.user),
    token: data?.access_token,
    tokenType: data?.token_type || 'bearer',
  }
}

export async function registerUser(fullName, email, password) {
  if (!fullName || !email || !password) {
    throw new Error('All fields are required.')
  }

  const data = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
  })

  if (data?.access_token) {
    setAuthToken(data.access_token)
  }

  return {
    user: mapUser(data?.user),
    token: data?.access_token,
    tokenType: data?.token_type || 'bearer',
  }
}

export async function getCurrentUser() {
  return mapUser(
    await request('/auth/me', {
      method: 'GET',
    })
  )
}

export async function forgotPassword(email) {
  if (!email) {
    throw new Error('Email is required.')
  }

  return request('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({
      email,
    }),
  })
}

export async function resetPassword(token, newPassword) {
  if (!token || !newPassword) {
    throw new Error('Reset token and new password are required.')
  }

  return request('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  })
}

export async function changePassword(currentPassword, newPassword) {
  return request('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  })
}

export async function deleteAccount() {
  const token = getStoredToken()

  const response = await fetch(`${API_URL}/auth/account`, {
    method: 'DELETE',

    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : {},
  })

  if (!response.ok) {
    const data = await parseResponse(response)

    const message =
      typeof data?.detail === 'string'
        ? data.detail
        : 'Unable to delete account.'

    const error = new Error(message)

    error.status = response.status
    error.data = data

    throw error
  }

  clearAuthToken()
}

// ---------------------------------------------------------------------------
// Skin analysis
// ---------------------------------------------------------------------------

export const ANALYSIS_TRACKS = [
  {
    id: 'facial_concerns',
    label: 'Facial skin concerns',
    description:
      'Acne, blackheads, dark spots, pores, wrinkles, oiliness, dryness, redness and eye bags on the face.',
    available: false,
  },
  {
    id: 'disease_screening',
    label: 'Skin disease screening support',
    description:
      'Conditions such as eczema or psoriasis on the face or body. Not available yet: it needs clinical review and independent validation first.',
    available: false,
  },
]

export async function analyzeSkin(imageFile, track = 'facial_concerns') {
  if (!imageFile) {
    throw new Error('Please select a skin image.')
  }

  const formData = new FormData()

  formData.append('file', imageFile)
  formData.append('track', track)

  return mapAnalysis(
    await request('/analyses/analyze', {
      method: 'POST',
      body: formData,
    })
  )
}

export async function getAnalysis(analysisId) {
  return request(
    `/analyses/${encodeURIComponent(analysisId)}`,
    {
      method: 'GET',
    }
  )
}

// ---------------------------------------------------------------------------
// Ingredient scanner
// ---------------------------------------------------------------------------

export async function scanIngredients(
  imageFile,
  ingredientsText = '',
  productName = ''
) {
  if (!imageFile && !ingredientsText) {
    throw new Error(
      'Please select an ingredient image or enter ingredients manually.'
    )
  }

  const formData = new FormData()

  if (imageFile) {
    formData.append('image', imageFile)
  }

  if (ingredientsText) {
    formData.append('ingredients_text', ingredientsText)
  }

  if (productName) {
    formData.append('product_name', productName)
  }

  return mapScan(
    await request('/scans/scan', {
      method: 'POST',
      body: formData,
    })
  )
}

export async function getScan(scanId) {
  return mapScan(
    await request(
      `/scans/${encodeURIComponent(scanId)}`,
      {
        method: 'GET',
      }
    )
  )
}

export async function getIngredients(params = {}) {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (
      value !== undefined &&
      value !== null &&
      value !== ''
    ) {
      query.set(key, value)
    }
  })

  const suffix = query.toString()
    ? `?${query.toString()}`
    : ''

  return request(`/ingredients${suffix}`, {
    method: 'GET',
  })
}

// ---------------------------------------------------------------------------
// AI Assistant
// ---------------------------------------------------------------------------

function mapChatMessage(item) {
  return {
    id: item?.id,
    role: item?.role || 'assistant',
    content: item?.content || '',
    imageUrl: assetUrl(item?.image_url),
    timestamp: item?.created_at,
  }
}

export async function sendChatMessage(message, language = 'auto') {
  if (!message || !message.trim()) {
    throw new Error('Message cannot be empty.')
  }

  const data = await request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: message.trim(),
      language,
    }),
  })

  return mapChatMessage(data)
}

export async function getChatHistory() {
  const data = await request('/chat/history', {
    method: 'GET',
  })

  return Array.isArray(data) ? data.map(mapChatMessage) : []
}

export async function getChatCapabilities() {
  return request('/chat/capabilities', { method: 'GET' })
}

export async function clearChatHistory() {
  await request('/chat/history', {
    method: 'DELETE',
  })

  // Backend returns HTTP 204 No Content.
  // The important thing is that the request completed successfully.
  return true
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

export async function getHistory() {
  return mapHistory(
    await request('/history', {
      method: 'GET',
    })
  )
}

// ---------------------------------------------------------------------------
// Progress
// ---------------------------------------------------------------------------

export async function checkProgress(beforeFile, afterFile) {
  if (!beforeFile || !afterFile) {
    throw new Error(
      'Both before and after images are required.'
    )
  }

  const formData = new FormData()

  formData.append('before_image', beforeFile)
  formData.append('after_image', afterFile)

  return mapProgress(
    await request('/progress', {
      method: 'POST',
      body: formData,
    })
  )
}

export async function getProgress() {
  const data = await request('/progress', {
    method: 'GET',
  })

  return Array.isArray(data)
    ? data.map(mapProgress)
    : []
}

export async function getProgressSummary() {
  return request('/progress/summary', {
    method: 'GET',
  })
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export async function generateReport(payload = {}) {
  const data = await request('/reports/generate', {
    method: 'POST',

    body: JSON.stringify({
      analysis_id: payload.analysis_id || null,
      progress_id: payload.progress_id || null,
      title:
        payload.title ||
        'Skyntri Health Report',
    }),
  })

  return {
    ...data,

    generatedAt: data.created_at,

    downloadUrl:
      `${API_URL}/reports/${encodeURIComponent(data.id)}/download`,
  }
}

export async function listReports() {
  return request('/reports', {
    method: 'GET',
  })
}

export async function downloadReport(reportId) {
  const token = getStoredToken()

  const response = await fetch(
    `${API_URL}/reports/${encodeURIComponent(reportId)}/download`,
    {
      method: 'GET',

      headers: token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {},
    }
  )

  if (!response.ok) {
    const data = await parseResponse(response)

    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'Unable to download report.'
    )
  }

  const blob = await response.blob()

  const disposition =
    response.headers.get('content-disposition') || ''

  const match =
    disposition.match(/filename="?([^"]+)"?/i)

  const filename =
    match?.[1] ||
    'skyntri-health-report.pdf'

  const url = window.URL.createObjectURL(blob)

  const link = document.createElement('a')

  link.href = url
  link.download = filename

  document.body.appendChild(link)

  link.click()

  link.remove()

  window.URL.revokeObjectURL(url)
}

// ---------------------------------------------------------------------------
// Profile / settings
// ---------------------------------------------------------------------------

export async function getProfile() {
  return mapUser(
    await request('/profile', {
      method: 'GET',
    })
  )
}

export async function updateProfile(payload) {
  const data = await request('/profile', {
    method: 'PUT',

    body: JSON.stringify({
      full_name:
        payload.fullName ??
        payload.full_name,

      skin_type:
        payload.skinType ??
        payload.skin_type,

      phone: payload.phone,
    }),
  })

  return mapUser(data)
}

export async function uploadAvatar(file) {
  if (!file) {
    throw new Error('Please select an avatar image.')
  }

  const formData = new FormData()

  formData.append('file', file)

  return mapUser(
    await request('/profile/avatar', {
      method: 'POST',
      body: formData,
    })
  )
}

export async function updateNotificationSettings(payload) {
  const data = await request(
    '/profile/notifications',
    {
      method: 'PUT',

      body: JSON.stringify({
        notify_analysis: Boolean(
          payload.notifyAnalysis ??
          payload.notify_analysis
        ),

        notify_reports: Boolean(
          payload.notifyReports ??
          payload.notify_reports
        ),
      }),
    }
  )

  return mapUser(data)
}

// ---------------------------------------------------------------------------
// Contact
// ---------------------------------------------------------------------------

export async function sendContactMessage(payload) {
  return request('/contact', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
// ---------------------------------------------------------------------------
// Analysis tracks (Model A / Model B availability comes from the backend)
// ---------------------------------------------------------------------------

export async function getAnalysisTracks() {
  try {
    const data = await request('/analyses/tracks', { method: 'GET' })
    return Array.isArray(data) ? data : ANALYSIS_TRACKS
  } catch {
    return ANALYSIS_TRACKS
  }
}

// ---------------------------------------------------------------------------
// Shop
// ---------------------------------------------------------------------------

export function mapProduct(product) {
  if (!product) return null
  return {
    ...product,
    imageUrl: assetUrl(product.image_url),
    priceCheckedAt: product.price_checked_at
      ? new Date(product.price_checked_at).toLocaleDateString()
      : null,
  }
}

function toQuery(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== false) {
      query.set(key, value)
    }
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export async function getProductMeta() {
  return request('/products/meta', { method: 'GET' })
}

export async function searchProducts(params = {}) {
  const data = await request(`/products${toQuery(params)}`, { method: 'GET' })
  return { ...data, items: (data?.items || []).map(mapProduct) }
}

export async function getProduct(productId) {
  return mapProduct(
    await request(`/products/${encodeURIComponent(productId)}`, { method: 'GET' })
  )
}

export async function getRecommendedProducts() {
  const data = await request('/products/recommended', { method: 'GET' })
  return { ...data, items: (data?.items || []).map(mapProduct) }
}

function mapCart(cart) {
  publishCartCount(cart?.item_count || 0)
  return {
    ...cart,
    items: (cart?.items || []).map((item) => ({ ...item, product: mapProduct(item.product) })),
  }
}

export async function getCart() {
  return mapCart(await request('/cart', { method: 'GET' }))
}

export async function addToCart(productId, quantity = 1) {
  return mapCart(
    await request('/cart/items', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, quantity }),
    })
  )
}

export async function updateCartItem(itemId, quantity) {
  return mapCart(
    await request(`/cart/items/${encodeURIComponent(itemId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ quantity }),
    })
  )
}

export async function removeCartItem(itemId) {
  return mapCart(
    await request(`/cart/items/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
  )
}

export async function placeOrder(shipping) {
  const order = await request('/orders', { method: 'POST', body: JSON.stringify(shipping) })
  publishCartCount(0)
  return order
}

export async function getOrders() {
  return request('/orders', { method: 'GET' })
}

export async function cancelOrder(orderId) {
  return request(`/orders/${encodeURIComponent(orderId)}/cancel`, { method: 'POST' })
}

// ---------------------------------------------------------------------------
// Shop administration (admin role required on the server)
// ---------------------------------------------------------------------------

export async function adminListProducts() {
  const data = await request('/admin/products', { method: 'GET' })
  return Array.isArray(data) ? data.map(mapProduct) : []
}

export async function adminCreateProduct(payload) {
  return mapProduct(
    await request('/admin/products', { method: 'POST', body: JSON.stringify(payload) })
  )
}

export async function adminUpdateProduct(productId, payload) {
  return mapProduct(
    await request(`/admin/products/${encodeURIComponent(productId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  )
}

export async function adminDeleteProduct(productId) {
  await request(`/admin/products/${encodeURIComponent(productId)}`, { method: 'DELETE' })
  return true
}

export async function adminUploadProductImage(productId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return mapProduct(
    await request(`/admin/products/${encodeURIComponent(productId)}/image`, {
      method: 'POST',
      body: formData,
    })
  )
}

export async function adminListOrders(status = '') {
  return request(`/admin/orders${toQuery({ status })}`, { method: 'GET' })
}

export async function adminUpdateOrderStatus(orderId, status) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

// ---------------------------------------------------------------------------
// Admin panel
// ---------------------------------------------------------------------------

export async function adminStats() {
  return request('/admin/stats', { method: 'GET' })
}

export async function adminListUsers(q = '') {
  return request(`/admin/users${toQuery({ q })}`, { method: 'GET' })
}

export async function adminUpdateUser(userId, payload) {
  return request(`/admin/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function adminUpdatePayment(orderId, paymentStatus) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ payment_status: paymentStatus }),
  })
}

// ---------------------------------------------------------------------------
// Account: Google sign-in, e-mail, first password
// ---------------------------------------------------------------------------

let publicConfigPromise = null

export function getPublicConfig() {
  if (!publicConfigPromise) {
    publicConfigPromise = request('/config', { method: 'GET' }).catch((error) => {
      publicConfigPromise = null
      throw error
    })
  }
  return publicConfigPromise
}

export async function loginWithGoogle(credential) {
  const data = await request('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  })

  if (data?.access_token) {
    setAuthToken(data.access_token)
  }

  return { user: mapUser(data?.user), token: data?.access_token }
}

export async function setPassword(newPassword) {
  return request('/auth/set-password', {
    method: 'POST',
    body: JSON.stringify({ new_password: newPassword }),
  })
}

export async function changeEmail(newEmail, currentPassword) {
  return mapUser(
    await request('/profile/email', {
      method: 'POST',
      body: JSON.stringify({ new_email: newEmail, current_password: currentPassword }),
    })
  )
}

// ---------------------------------------------------------------------------
// Clinic: doctors, appointments, messages, prescriptions
// ---------------------------------------------------------------------------

const json = (method, body) => ({ method, body: body === undefined ? undefined : JSON.stringify(body) })

function mapDoctor(doctor) {
  return doctor ? { ...doctor, avatarUrl: assetUrl(doctor.avatar_url) } : doctor
}

function mapAppointment(item) {
  if (!item) return item
  return {
    ...item,
    analysis: item.analysis ? { ...item.analysis, imageUrl: assetUrl(item.analysis.image_url) } : null,
  }
}

export const listDoctors = async () => (await request('/doctors')).map(mapDoctor)
export const getDoctor = async (id) => mapDoctor(await request(`/doctors/${encodeURIComponent(id)}`))
export const getDoctorSlots = (id, day) =>
  request(`/doctors/${encodeURIComponent(id)}/slots?day=${encodeURIComponent(day)}`)

export const applyAsDoctor = async (payload) => mapDoctor(await request('/doctors/apply', json('POST', payload)))
export async function getMyDoctorProfile() {
  try {
    return mapDoctor(await request('/doctors/me'))
  } catch (error) {
    if (error.status === 404) return null
    throw error
  }
}
export const updateMyDoctorProfile = async (payload) => mapDoctor(await request('/doctors/me', json('PUT', payload)))
export const setMyAvailability = async (windows) =>
  mapDoctor(await request('/doctors/me/availability', json('PUT', { windows })))

export const bookAppointment = async (payload) => mapAppointment(await request('/appointments', json('POST', payload)))
export const listMyAppointments = async () => (await request('/appointments')).map(mapAppointment)
export const getAppointment = async (id) => mapAppointment(await request(`/appointments/${encodeURIComponent(id)}`))
export const cancelAppointment = async (id, reason) =>
  mapAppointment(await request(`/appointments/${encodeURIComponent(id)}/cancel`, json('POST', { reason: reason || null })))

export const listAppointmentMessages = (id) => request(`/appointments/${encodeURIComponent(id)}/messages`)
export const sendAppointmentMessage = (id, body) =>
  request(`/appointments/${encodeURIComponent(id)}/messages`, json('POST', { body }))

export async function downloadPrescription(id) {
  const response = await fetch(`${API_URL}/appointments/${encodeURIComponent(id)}/prescription.pdf`, {
    headers: { Authorization: `Bearer ${getStoredToken()}` },
  })
  if (!response.ok) {
    const data = await parseResponse(response)
    throw new Error((data && data.detail) || 'The prescription could not be downloaded.')
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = 'skyntri-prescription.pdf'
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export const doctorListAppointments = async (scope = 'upcoming') =>
  (await request(`/doctor/appointments?scope=${scope}`)).map(mapAppointment)
export const doctorUpdateAppointment = async (id, payload) =>
  mapAppointment(await request(`/doctor/appointments/${encodeURIComponent(id)}`, json('PATCH', payload)))
export const doctorSavePrescription = (id, payload) =>
  request(`/doctor/appointments/${encodeURIComponent(id)}/prescription`, json('PUT', payload))
export const doctorListPatients = () => request('/doctor/patients')

export const adminListDoctors = async () => (await request('/admin/doctors')).map(mapDoctor)
export const adminReviewDoctor = async (id, status) =>
  mapDoctor(await request(`/admin/doctors/${encodeURIComponent(id)}`, json('PATCH', { status })))
export const adminListAppointments = async (status) =>
  (await request(`/admin/appointments${status ? `?status=${status}` : ''}`)).map(mapAppointment)
export const adminSetAppointmentPayment = async (id, paymentStatus) =>
  mapAppointment(
    await request(`/admin/appointments/${encodeURIComponent(id)}/payment?payment_status=${paymentStatus}`, json('PATCH'))
  )

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------

export const getPaymentMethods = (purpose, referenceId) =>
  request(`/payments/methods?purpose=${purpose}&reference_id=${encodeURIComponent(referenceId)}`)
export const startCheckout = (purpose, referenceId, provider) =>
  request('/payments/checkout', json('POST', { purpose, reference_id: referenceId, provider }))
export const confirmPayment = (id) => request(`/payments/${encodeURIComponent(id)}/confirm`, json('POST'))
export const cancelPayment = (id) => request(`/payments/${encodeURIComponent(id)}/cancel`, json('POST'))
export const adminListPayments = () => request('/admin/payments')

// Only ever send the browser to the payment providers' own pages.
const PAYMENT_HOSTS = /^(checkout\.stripe\.com|getsafepay\.com|sandbox\.api\.getsafepay\.com|www\.paypal\.com|www\.sandbox\.paypal\.com)$/

export function isSafePaymentUrl(url) {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' && PAYMENT_HOSTS.test(parsed.hostname)
  } catch {
    return false
  }
}

// ---------------------------------------------------------------------------
// Admin: settings, automation, posts
// ---------------------------------------------------------------------------

export const adminGetSettings = () => request('/admin/settings')
export const adminUpdateSetting = (key, value) => request('/admin/settings', json('PUT', { key, value }))
export const adminAuditLog = () => request('/admin/audit?limit=50')
export const adminTestConnection = (name) => request(`/admin/connections/${encodeURIComponent(name)}/test`, json('POST'))

export const adminAutomation = () => request('/admin/automation')
export const adminCreateApiKey = (name, scopes) => request('/admin/automation/api-keys', json('POST', { name, scopes }))
export const adminRevokeApiKey = (id) => request(`/admin/automation/api-keys/${encodeURIComponent(id)}`, json('DELETE'))
export const adminCreateWebhook = (payload) => request('/admin/automation/webhooks', json('POST', payload))
export const adminGetWebhook = (id) => request(`/admin/automation/webhooks/${encodeURIComponent(id)}`)
export const adminUpdateWebhook = (id, payload) =>
  request(`/admin/automation/webhooks/${encodeURIComponent(id)}`, json('PUT', payload))
export const adminDeleteWebhook = (id) => request(`/admin/automation/webhooks/${encodeURIComponent(id)}`, json('DELETE'))
export const adminTestWebhook = (id) => request(`/admin/automation/webhooks/${encodeURIComponent(id)}/test`, json('POST'))
export const adminRunAgent = (name) => request(`/admin/automation/agents/${encodeURIComponent(name)}/run`, json('POST'))

export const adminListPosts = () => request('/admin/posts')
export const adminCreatePost = (payload) => request('/admin/posts', json('POST', payload))
export const adminUpdatePost = (id, payload) => request(`/admin/posts/${encodeURIComponent(id)}`, json('PATCH', payload))
export const adminDeletePost = (id) => request(`/admin/posts/${encodeURIComponent(id)}`, json('DELETE'))
export const getPosts = (limit = 3) => request(`/posts?limit=${limit}`)
