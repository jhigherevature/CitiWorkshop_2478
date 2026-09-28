import { Container } from '@mui/material'
import BookGrid from './components/BookGrid.jsx'
import LoginForm from './components/LoginForm.jsx'
import { useAuth } from './context/AuthContext.jsx'

export default function App() {
  const { user } = useAuth()

  return (
    <Container sx={{ mt: 4 }}>
      {user ? <BookGrid /> : <LoginForm />}
    </Container>
  )
}
