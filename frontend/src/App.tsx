import { useState, useEffect } from 'react';
import { useFleetStore } from './store/useFleetStore';
import { useBookmarkStore } from './store/useBookmarkStore';
import { useSSE } from './hooks/useSSE';
import { Bar, Line } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

Chart.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Title, Tooltip, Legend);

function App() {
  useSSE('http://localhost:8000/alerts/stream');
  const alerts = useFleetStore((state) => state.alerts);
  const { starredTrips, toggleBookmark } = useBookmarkStore();
  const [tab, setTab] = useState<'live' | 'history' | 'bookmarks'>('live');
  const [liveFilter, setLiveFilter] = useState('');

  // Extract unique trip IDs currently in the live buffer for the datalist
  const uniqueLiveTrips = Array.from(new Set(alerts.map(a => a.trip_id)));

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Fleet Fuel Saver Dashboard</h1>
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button onClick={() => setTab('live')} style={{ padding: '10px', background: tab === 'live' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Live Stream</button>
        <button onClick={() => setTab('history')} style={{ padding: '10px', background: tab === 'history' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Historical Analytics</button>
        <button onClick={() => setTab('bookmarks')} style={{ padding: '10px', background: tab === 'bookmarks' ? '#007bff' : '#ccc', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>⭐ Bookmarks</button>
      </div>

      {tab === 'live' && (
        <div>
          <div style={{ marginBottom: '15px' }}>
            <input 
              list="live-trips"
              type="text" 
              placeholder="Filter by Trip ID (e.g. csv-vehicle-001)..." 
              value={liveFilter} 
              onChange={(e) => setLiveFilter(e.target.value)} 
              style={{ padding: '8px', width: '300px', borderRadius: '4px', border: '1px solid #ccc' }}
            />
            <datalist id="live-trips">
              {uniqueLiveTrips.map(id => <option key={id} value={id} />)}
            </datalist>
            {liveFilter && (
              <button onClick={() => setLiveFilter('')} style={{ padding: '8px 15px', marginLeft: '10px', cursor: 'pointer' }}>Clear</button>
            )}
          </div>

          <div style={{ display: 'grid', gap: '10px' }}>
            {alerts
              .filter(a => a.trip_id.toLowerCase().includes(liveFilter.toLowerCase()))
              .map((a, i) => (
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
            {alerts.length > 0 && alerts.filter(a => a.trip_id.toLowerCase().includes(liveFilter.toLowerCase())).length === 0 && (
              <p>No alerts match that Trip ID.</p>
            )}
          </div>
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
  const [timeseries, setTimeseries] = useState<any[]>([]);
  const [historyAlerts, setHistoryAlerts] = useState<any[]>([]);
  const [filterTrip, setFilterTrip] = useState('');
  const [filterHours, setFilterHours] = useState(1);

  const fetchAllData = (trip = filterTrip, hours = filterHours) => {
    const queryArgs = new URLSearchParams();
    if (trip) queryArgs.append('trip_id', trip);
    queryArgs.append('hours', hours.toString());
    const query = `?${queryArgs.toString()}`;
    
    fetch(`http://localhost:8000/history/stats${query}`)
      .then(res => res.json())
      .then(d => setStats(d.data || []))
      .catch(e => console.error("Stats API failed", e));
      
    fetch(`http://localhost:8000/history/timeseries${query}`)
      .then(res => res.json())
      .then(d => setTimeseries(d.data || []))
      .catch(e => console.error("Timeseries API failed", e));
      
    fetch(`http://localhost:8000/history/alerts${query}&limit=50`)
      .then(res => res.json())
      .then(d => setHistoryAlerts(d.data || []))
      .catch(e => console.error("Alerts API failed", e));
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleSearch = () => fetchAllData(filterTrip, filterHours);

  const barChartData = {
    labels: stats.map(s => s.name),
    datasets: [{
      label: 'Total Alerts',
      data: stats.map(s => s.value),
      backgroundColor: '#f57c00'
    }]
  };
  
  const lineChartData = {
    labels: timeseries.map(t => new Date(t.bucket).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})),
    datasets: [{
      label: 'Alerts per Minute',
      data: timeseries.map(t => t.count),
      borderColor: '#1976d2',
      backgroundColor: 'rgba(25, 118, 210, 0.2)',
      fill: true,
      tension: 0.3
    }]
  };

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '40px' }}>
        <div>
          <h3>Alerts by Type {filterTrip ? `(${filterTrip})` : ''} ({filterHours === 1 ? 'Last Hour' : filterHours === 24 ? 'Last 24 Hours' : 'Last 7 Days'})</h3>
          <div style={{ height: '300px', position: 'relative' }}>
            {stats.length > 0 ? <Bar data={barChartData} options={{ maintainAspectRatio: false }} /> : <p>Loading chart...</p>}
          </div>
        </div>
        <div>
          <h3>Alert Velocity {filterTrip ? `(${filterTrip})` : ''} ({filterHours === 1 ? 'Last Hour' : filterHours === 24 ? 'Last 24 Hours' : 'Last 7 Days'})</h3>
          <div style={{ height: '300px', position: 'relative' }}>
            {timeseries.length > 0 ? <Line data={lineChartData} options={{ maintainAspectRatio: false }} /> : <p>Loading time-series...</p>}
          </div>
        </div>
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
          <select 
            value={filterHours} 
            onChange={(e) => {
              const newHours = Number(e.target.value);
              setFilterHours(newHours);
              fetchAllData(filterTrip, newHours);
            }} 
            style={{ padding: '8px', marginRight: '10px' }}
          >
            <option value={1}>Last 1 Hour</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last 7 Days</option>
          </select>
          <button onClick={handleSearch} style={{ padding: '8px' }}>Search</button>
          <button onClick={() => { setFilterTrip(''); setFilterHours(1); fetchAllData('', 1); }} style={{ padding: '8px', marginLeft: '10px' }}>Clear</button>
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
