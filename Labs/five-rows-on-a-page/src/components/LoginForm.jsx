import { useState } from 'react'
import { Button, Stack, TextField, Typography } from '@mui/material'
import { useAuth } from '../context/AuthContext.jsx'

export default function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
  }

  return (
    <Stack component="form" spacing={2} sx={{ maxWidth: 320 }} onSubmit={handleSubmit}>
      <Typography variant="h5">Sign in</Typography>
      <TextField
        label="Username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <TextField
        label="Password"
        type="password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />
      <Button type="submit" variant="contained">
        Sign in
      </Button>
    </Stack>
  )
}
