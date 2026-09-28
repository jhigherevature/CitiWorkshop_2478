import { createContext, useContext, useState } from 'react'
import client, { setToken } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)

  async function login(username, password) {
    const form = new URLSearchParams({ username, password })
    const response = await client.post('/auth/login', form)
    setToken(response.data.access_token)
    setUser(username)
  }

  return (
    <AuthContext value={{ user, login }}>
      {children}
    </AuthContext>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
