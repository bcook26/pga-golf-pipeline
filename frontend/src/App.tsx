import { Link, NavLink, Route, Routes } from 'react-router-dom'

import { useTheme } from './lib/useTheme'
import { ComparePage } from './pages/ComparePage'
import { LeadersPage } from './pages/LeadersPage'
import { PipelinePage } from './pages/PipelinePage'
import { PlayerPage } from './pages/PlayerPage'
import { PlayersPage } from './pages/PlayersPage'
import { StatsPage } from './pages/StatsPage'
import { TournamentPage } from './pages/TournamentPage'
import { TournamentsPage } from './pages/TournamentsPage'

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
          <NavLink to="/tournaments">Tournaments</NavLink>
          <NavLink to="/compare">Compare Players</NavLink>
          <NavLink to="/stats">Stats</NavLink>
          <NavLink to="/pipeline">Pipeline Health</NavLink>
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
          <Route path="/tournaments" element={<TournamentsPage />} />
          <Route path="/tournaments/:id" element={<TournamentPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
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
