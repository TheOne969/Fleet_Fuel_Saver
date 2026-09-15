import { useState, useEffect } from 'react';
import { useFleetStore } from './store/useFleetStore';
import { useBookmarkStore } from './store/useBookmarkStore';
import { useSSE } from './hooks/useSSE';
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

Chart.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

function App() {
  useSSE('http://localhost:8000/alerts/stream');
  const alerts = useFleetStore((state) => state.alerts);
  const { starredTrips, toggleBookmark } = useBookmarkStore();
  const [tab, setTab] = useState<'live' | 'history' | 'bookmarks'>('live');

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Fleet Fuel Saver Dashboard</h1>
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button onClick={() => setTab('live')} style={{ padding: '10px', background: tab === 'live' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Live Stream</button>
        <button onClick={() => setTab('history')} style={{ padding: '10px', background: tab === 'history' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Historical Analytics</button>
        <button onClick={() => setTab('bookmarks')} style={{ padding: '10px', background: tab === 'bookmarks' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>⭐ Bookmarks</button>
      </div>

      {tab === 'live' && (
        <div style={{ display: 'grid', gap: '10px' }}>
          {alerts.map((a, i) => (
            <div key={i} style={{ 
                padding: '10px', 
                border: `1px solid ${a.severity === 'HIGH' ? 'red' : 'orange'}`, 
                borderRadius: '4px', 
                background: a.severity === 'HIGH' ? '#fee' : '#fff3e0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
              <div>
                <strong>{a.trip_id}</strong> - <span style={{ color: a.severity === 'HIGH' ? 'red' : 'orange', fontWeight: 'bold' }}>{a.type}</span>
                <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#555' }}>{a.reason}</p>
              </div>
              <button 
                onClick={() => toggleBookmark(a.trip_id)}
                style={{ fontSize: '24px', background: 'none', border: 'none', cursor: 'pointer' }}
                title="Bookmark Trip"
              >
                {starredTrips.includes(a.trip_id) ? '⭐' : '☆'}
              </button>
            </div>
          ))}
          {alerts.length === 0 && <p>No alerts currently.</p>}
        </div>
      )}

      {tab === 'history' && <HistoryTab starredTrips={starredTrips} toggleBookmark={toggleBookmark} />}

      {tab === 'bookmarks' && (
        <div>
          <h3>Starred Vehicles</h3>
          {starredTrips.length === 0 ? (
            <p>No trips bookmarked yet. Click the star next to an alert to track that vehicle!</p>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {starredTrips.map(id => (
                <div key={id} style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>Trip: {id}</strong>
                  <button onClick={() => toggleBookmark(id)} style={{ padding: '5px 10px', background: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Remove</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HistoryTab({ starredTrips, toggleBookmark }: { starredTrips: string[], toggleBookmark: (id: string) => void }) {
  const [stats, setStats] = useState<any[]>([]);
  const [historyAlerts, setHistoryAlerts] = useState<any[]>([]);
  const [filterTrip, setFilterTrip] = useState('');

  useEffect(() => {
    fetch('http://localhost:8000/history/stats')
      .then(res => res.json())
      .then(d => setStats(d.data || []))
      .catch(e => console.error("Stats API failed", e));
    fetchAlerts();
  }, []);

  const fetchAlerts = (trip = '') => {
    fetch(`http://localhost:8000/history/alerts?limit=50${trip ? `&trip_id=${trip}` : ''}`)
      .then(res => res.json())
      .then(d => setHistoryAlerts(d.data || []))
      .catch(e => console.error("Alerts API failed", e));
  };

  const handleSearch = () => fetchAlerts(filterTrip);

  const chartData = {
    labels: stats.map(s => s.name),
    datasets: [{
      label: 'Total Alerts',
      data: stats.map(s => s.value),
      backgroundColor: '#f57c00'
    }]
  };

  return (
    <div>
      <div style={{ height: '300px', marginBottom: '40px' }}>
        <h3>Alerts by Type (All Time)</h3>
        {stats.length > 0 ? <Bar data={chartData} options={{ maintainAspectRatio: false }} /> : <p>Loading chart...</p>}
      </div>

      <div>
        <h3>Historical Alerts</h3>
        <div style={{ marginBottom: '10px' }}>
          <input 
            value={filterTrip} 
            onChange={(e) => setFilterTrip(e.target.value)} 
            placeholder="Filter by Trip ID..." 
            style={{ padding: '8px', marginRight: '10px' }}
          />
          <button onClick={handleSearch} style={{ padding: '8px' }}>Search</button>
          <button onClick={() => { setFilterTrip(''); fetchAlerts(''); }} style={{ padding: '8px', marginLeft: '10px' }}>Clear</button>
        </div>
        
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', textAlign: 'left' }}>
              <th style={{ padding: '10px', borderBottom: '1px solid #ccc' }}>⭐</th>
              <th style={{ padding: '10px', borderBottom: '1px solid #ccc' }}>Time</th>
              <th style={{ padding: '10px', borderBottom: '1px solid #ccc' }}>Trip ID</th>
              <th style={{ padding: '10px', borderBottom: '1px solid #ccc' }}>Type</th>
              <th style={{ padding: '10px', borderBottom: '1px solid #ccc' }}>Severity</th>
            </tr>
          </thead>
          <tbody>
            {historyAlerts.map((a, i) => (
              <tr key={i}>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>
                  <button onClick={() => toggleBookmark(a.trip_id)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}>
                    {starredTrips.includes(a.trip_id) ? '⭐' : '☆'}
                  </button>
                </td>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{new Date(a.timestamp).toLocaleString()}</td>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{a.trip_id}</td>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee' }}>{a.type}</td>
                <td style={{ padding: '10px', borderBottom: '1px solid #eee', color: a.severity === 'HIGH' ? 'red' : 'orange' }}>{a.severity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
