import { useEffect, useState } from 'react'
import { DataGrid } from '@mui/x-data-grid'
import client from '../api/client.js'

const columns = [
  { field: 'title', headerName: 'Title', flex: 1 },
  { field: 'author', headerName: 'Author', flex: 1 },
  { field: 'genre', headerName: 'Genre', width: 160 },
]

export default function BookGrid() {
  const [books, setBooks] = useState([])

  useEffect(() => {
    client.get('/books').then((response) => setBooks(response.data))
  }, [])

  return (
    <div style={{ height: 400 }}>
      <DataGrid rows={books} columns={columns} />
    </div>
  )
}
