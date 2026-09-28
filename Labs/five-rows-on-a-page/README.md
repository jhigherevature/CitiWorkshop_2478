# Five Rows on a Page

We'll build a React frontend that logs in against a real API and renders data it can only get with a token. Along the way we'll look at the Vite project layout, an axios instance, a request interceptor that attaches the token, React Context holding auth state, conditional rendering on login state, and MUI's DataGrid.

## Prerequisites

| Software | Required Version |
|---|---|
| Node.js | 20.19+ or 22.12+ (required by Vite 8) |
| Vite | 8.3 |
| React | 19.3 |
| MUI (`@mui/material`) | 9.4 |
| MUI X Data Grid (`@mui/x-data-grid`) | 9.14 (the free MIT version) |
| axios | 1.20 |
| Python (for the `api/` folder) | 3.10 or newer (3.14 is current) |
| FastAPI (for the `api/` folder) | 0.141.1 |

`npm install` and `pip install -r requirements.txt` fetch all the packages. Only Node.js and Python need to be installed beforehand.

### About the `api/` folder

`api/main.py` is **scenery**. It's a single-file FastAPI backend, a stripped-down *Login and a Locked Door*, with one user and five books held in a Python list. It has two endpoints: `POST /auth/login` and a locked `GET /books`. We don't change it, and this lab isn't about it. It's here because a login form with no server to log in to doesn't teach anything.

It also has CORS middleware, because the frontend (`localhost:5173`) and the API (`127.0.0.1:8000`) are different origins, and the browser won't let one talk to the other unless the API says it may.

### Getting it running

We need **two terminals**, one for each half.

**Terminal 1: the API.** From this folder:

macOS / Linux:

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Windows (PowerShell):

```powershell
cd api
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

(If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope Process Bypass` first.) Leave it running.

**Terminal 2: the frontend.** From this folder (*not* `api/`):

```bash
npm install
npm run dev
```

Open **http://localhost:5173**. The login is `reader` / `reader123`.

If Vite says port 5173 is in use and picks 5174 instead, stop the other dev server and start this one again. The API only accepts requests from pages on port 5173.

## Guided walkthrough

### The Vite project layout

At the top level, next to this README:

- **`package.json`** lists our dependencies and the `dev` script we just ran.
- **`vite.config.js`** loads Vite's React plugin, which compiles JSX and keeps the page updated as we save files.
- **`index.html`** is the real entry point. It's nearly empty: a `<div id="root">` and a `<script>` tag pointing at `src/main.jsx`. Vite serves this page and follows the imports from there.

We scaffolded with `npm create vite@latest` and then took out the demo counter app, its CSS, its logo images, and the lint setup. What's left in `src/` is ours:

| File | Its job |
|---|---|
| `src/main.jsx` | Mounts the app into `#root`, wrapped in `AuthProvider` |
| `src/App.jsx` | Decides which screen to show |
| `src/api/client.js` | The one axios instance every request goes through, and the only code that touches the token |
| `src/context/AuthContext.jsx` | Holds who's logged in, and provides `login()` |
| `src/components/LoginForm.jsx` | The sign-in form |
| `src/components/BookGrid.jsx` | Fetches `/books` and shows it in a DataGrid |

Keep one thing in mind as we read them: **the token lives in `client.js` and nowhere else.** Components never see it.

### 1. `api/client.js`: one axios instance

```js
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
```

- **`axios.create`** gives us our own configured instance. With `baseURL` set, the rest of the app writes `client.get('/books')` and never repeats the server address.
- **`token`** is a plain variable, private to this module. `setToken` is the only way to change it.
- **The interceptor** is a function axios runs on every request, just before sending it. It gets the request's settings (`config`), can change them, and hands them back. Ours does one thing: if we have a token, it adds the `Authorization` header.

This is the only place in the app that knows the header exists. If each component attached the header itself, the first one somebody forgot would fail with a `401`. Here, a request made through `client` can't leave without it.

### 2. `context/AuthContext.jsx`: who's logged in

```jsx
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
```

- **`login`** posts the username and password as a `URLSearchParams`. axios sends that as a form (`application/x-www-form-urlencoded`), which is the format `OAuth2PasswordRequestForm` expects and what Swagger's **Authorize** button sent in the last lab.
- On success the two results go to two places. The **token** goes to `client.js`, for requests. The **username** goes into React state, for rendering. Setting state is what makes React re-render. Setting the token re-renders nothing, and nothing needs it to.
- **`<AuthContext value={...}>`** makes `user` and `login` available to everything inside it. In React 19 the context itself works as the provider. Older code writes `<AuthContext.Provider value={...}>`, which does the same thing.
- **`useAuth()`** is a shorthand so components don't import both `useContext` and `AuthContext`.

### 3. `main.jsx` and `App.jsx`: choosing a screen

```jsx
createRoot(document.getElementById('root')).render(
  <AuthProvider>
    <App />
  </AuthProvider>,
)
```

`AuthProvider` wraps `App`, so anything inside it can call `useAuth()`. The Vite template also wraps the app in `<StrictMode>`, which in development runs every effect twice to shake out bugs. We've taken it out so each request appears exactly once in the network tab.

```jsx
export default function App() {
  const { user } = useAuth()

  return (
    <Container sx={{ mt: 4 }}>
      {user ? <BookGrid /> : <LoginForm />}
    </Container>
  )
}
```

There's no router. One piece of state picks the screen. When `login` calls `setUser`, `App` re-renders and swaps `LoginForm` for `BookGrid`. That also means `BookGrid` doesn't exist until after login, so its request for books can't go out before there's a token to send with it.

### 4. `components/BookGrid.jsx`: the grid

```jsx
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
```

- **`useEffect(..., [])`** runs once, when the grid first appears. It asks for `/books` and stores the result. There's nothing about tokens or headers here.
- **`rows`** is the array from the API. The DataGrid needs an `id` on every row, and our API sends one.
- **`columns`** says which fields to show and how. Each `field` matches a key in the JSON.
- **The `div` with a height** is there because the DataGrid fills whatever space its parent gives it. With no height on the parent, it has nothing to fill.

### 5. Wiring the form to the context

Here's `LoginForm.jsx` as it stands:

```jsx
export default function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
  }

  return (
    <Stack component="form" spacing={2} sx={{ maxWidth: 320 }} onSubmit={handleSubmit}>
      ...
    </Stack>
  )
}
```

The fields keep their values in state, and `handleSubmit` stops the browser from reloading the page on submit. That's all it does. Try signing in now: nothing happens, because nothing sends the form anywhere.

We'll connect it to the context. First, at the top of the component, above the two `useState` lines, we'll ask the context for its `login` function:

```jsx
  const { login } = useAuth()
```

Then inside `handleSubmit`, after `event.preventDefault()`, we'll call it:

```jsx
    await login(username, password)
```

so the top of the component reads:

```jsx
export default function LoginForm() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    await login(username, password)
  }
```

`useAuth` is already imported. Save, go back to the browser, and sign in as `reader` / `reader123`. The form disappears and the grid fills with five books.

That one line started all of this:

1. `LoginForm` calls `login()` from the context.
2. The context posts to `/auth/login` through `client` and gets a token back.
3. The token goes into `client.js`, and `setUser('reader')` goes into state.
4. `App` re-renders, sees a user, and mounts `BookGrid`.
5. `BookGrid` calls `client.get('/books')`.
6. The interceptor adds the header, the API answers `200`, and the grid fills.

### 6. One more column

The grid shows three columns, but the API sends more than that. In `src/components/BookGrid.jsx`, add a fourth entry to `columns`, right after `genre`:

```jsx
  { field: 'pages', headerName: 'Pages', type: 'number', width: 100 },
```

Save and sign in again (saving may have sent you back to the login form). There's now a **Pages** column. We didn't change the request or the API. The page counts were in every response all along (so is `available`), and the column list decides what's shown. `type: 'number'` right-aligns the values and sorts them as numbers rather than text.

### 7. The interceptor at work

This is the part worth slowing down for. Open the browser's developer tools (**F12**), go to the **Network** tab, and click the **Fetch/XHR** filter. Now reload the page. You're back at the login form (we'll see why in the next step). Sign in again and watch the requests arrive:

- **`login`** (POST). Click it and look at **Headers → Request Headers**. There's no `Authorization` header. We didn't have a token yet, so the interceptor had nothing to add.
- **`books`** (OPTIONS). Depending on the browser you may see this one; Chrome and Edge label it *preflight*. It's the browser asking the API, on its own initiative, "will you accept a request from `localhost:5173` that carries an `Authorization` header?" The CORS middleware in `api/main.py` says yes.
- **`books`** (GET). Look at its **Request Headers**:

  ```
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ```

Now open `src/components/BookGrid.jsx` again. The request there is `client.get('/books')`, with no header and no token. Search all of `src/` for `Authorization` and you'll find it exactly once, in `client.js`. **No component put that header there.** Every request made through `client`, from any component we have now or add later, carries it. That's why a full application can add twenty endpoints without writing any auth code for them.

While the network tab is open, sign out by reloading, then sign in with a wrong password. Nothing changes on screen, but `login` shows a **401** and the console shows an uncaught `AxiosError`. That's the error handling this lab leaves out.

### 8. Why a reload logs us out

Every reload has put us back at the login form. That's because the token was a variable in `client.js` and the user was React state. Both live in the page's memory, and a reload throws that memory away. We never wrote anything to `localStorage`, `sessionStorage`, or a cookie.

A full application often stores the token (in `localStorage`, say) so a reload keeps the user signed in. That's a real design choice with a security trade-off, since any script running on the page can read `localStorage`. This lab keeps the token in memory so every step of the flow happens where we can see it.

## What this lab leaves out

These are deliberate: routing, logout, loading and error states, styling beyond MUI's defaults, form validation, token refresh, and tests. Each one would be more code standing between us and the interceptor.
