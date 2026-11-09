import { Link, NavLink, Route, Routes } from 'react-router-dom'

import { useTheme } from './lib/useTheme'
import { ComparePage } from './pages/ComparePage'
import { LeadersPage } from './pages/LeadersPage'
import { PlayerPage } from './pages/PlayerPage'
import { PlayersPage } from './pages/PlayersPage'

export default function App() {
  const { theme, cycle } = useTheme()
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <Link to="/" className="brand">
          Golf Stats
        </Link>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Players
          </NavLink>
          <NavLink to="/leaders">Leaderboards</NavLink>
          <NavLink to="/compare">Compare</NavLink>
        </nav>
        <button type="button" className="theme" onClick={cycle} aria-label={`Theme: ${theme}. Click to change`}>
          Theme: {theme}
        </button>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<PlayersPage />} />
          <Route path="/players/:id" element={<PlayerPage />} />
          <Route path="/leaders" element={<LeadersPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route
            path="*"
            element={
              <>
                <h1>Page not found</h1>
                <Link to="/">Back to players</Link>
              </>
            }
          />
        </Routes>
      </main>
    </>
  )
}
