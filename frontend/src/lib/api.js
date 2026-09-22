import axios from 'axios'

const TOKEN_KEY = 'cricket_connect_token'
const USER_KEY = 'cricket_connect_user'
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})
const getStoredToken = () => {
  const value = localStorage.getItem(TOKEN_KEY)?.trim()
  return value ? value.replace(/^Bearer\s+/i, '') : ''
}
client.interceptors.request.use(config => {
  const token = getStoredToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = 'Bearer ' + token
  }
  return config
})

const data = response => response.data
const list = value => Array.isArray(value) ? value : value?.items || value?.results || value?.data || []
const readableValue = value => {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(readableValue).filter(Boolean).join(' ')
  if (value && typeof value === 'object') {
    if (value.msg) {
      const location = Array.isArray(value.loc) ? value.loc.filter(part => part !== 'body').join('.') : ''
      return location ? `${location}: ${value.msg}` : value.msg
    }
    if (value.message) return readableValue(value.message)
    try { return JSON.stringify(value) } catch { return 'The server returned an unexpected error.' }
  }
  return value == null ? '' : String(value)
}
const message = error => {
  if (!error.response) return error.request ? 'Unable to reach the server. Check that the backend is running and try again.' : (error.message || 'Something went wrong.')
  const payload = error.response.data
  const detail = payload?.detail ?? payload?.message ?? payload
  return readableValue(detail) || `Request failed with status ${error.response.status}.`
}
async function request(path, options) {
  try { return data(await client({ url: path, ...options })) } catch (error) {
    const normalized = new Error(message(error))
    normalized.status = error.response?.status
    normalized.cause = error
    throw normalized
  }
}

export const api = {
  sessions: params => request('/sessions/search', { params }).then(list),
  session: id => request('/sessions/search').then(list).then(items => items.find(item => String(item.id) === String(id))),
  venues: () => request('/venues').then(list),
  venue: id => request(`/venues/${id}`),
  bookings: () => request('/bookings/mine').then(list),
  createBooking: sessionId => request('/bookings', { method: 'POST', data: { session_id: sessionId } }),
}
export const authApi = {
  login: credentials => request('/auth/login', { method: 'POST', data: credentials }),
  register: details => request('/auth/register', { method: 'POST', data: details }),
}
export function setStoredAuth(result) {
  if (!result) {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    return
  }
  const token = result.access_token || result.token || result.data?.access_token
  const user = result.user || result.data?.user || result
  if (token) localStorage.setItem(TOKEN_KEY, String(token).replace(/^Bearer\s+/i, ''))
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}
export function getStoredUser() { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null } }
