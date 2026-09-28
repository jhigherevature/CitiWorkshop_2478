import axios from 'axios'

let token = null

export function setToken(newToken) {
  token = newToken
}

const client = axios.create({
  baseURL: 'http://127.0.0.1:8000',
})

client.interceptors.request.use((config) => {
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default client
