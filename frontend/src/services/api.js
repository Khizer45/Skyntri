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

    track: data?.analysis_track || 'facial_concerns',
    trackLabel: data?.analysis_track_label || 'Facial skin concerns',
    modelVersion: data?.model_version || '',

    explanation: conditions.length
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
    available: true,
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

export async function sendChatMessage(message) {
  if (!message || !message.trim()) {
    throw new Error('Message cannot be empty.')
  }

  const data = await request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: message.trim(),
    }),
  })

  return {
    id: data?.id,
    role: data?.role || 'assistant',
    content: data?.content || '',
    timestamp: data?.created_at,
  }
}

export async function getChatHistory() {
  const data = await request('/chat/history', {
    method: 'GET',
  })

  if (!Array.isArray(data)) {
    return []
  }

  return data.map((item) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    timestamp: item.created_at,
  }))
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