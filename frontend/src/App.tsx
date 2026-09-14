import { useFleetStore } from './store/useFleetStore';
import { useSSE } from './hooks/useSSE';

function App() {
  useSSE('http://localhost:8000/alerts/stream');
  const alerts = useFleetStore((state) => state.alerts);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Live Fleet Alerts</h1>
      <div style={{ display: 'grid', gap: '10px' }}>
        {alerts.map((a, i) => (
          <div key={i} style={{ 
              padding: '10px', 
              border: `1px solid ${a.severity === 'HIGH' ? 'red' : 'orange'}`, 
              borderRadius: '4px', 
              background: a.severity === 'HIGH' ? '#fee' : '#fff3e0' 
            }}>
            <strong>{a.trip_id}</strong> - <span style={{ color: a.severity === 'HIGH' ? 'red' : 'orange', fontWeight: 'bold' }}>{a.type}</span>
            <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#555' }}>{a.reason}</p>
          </div>
        ))}
        {alerts.length === 0 && <p>No alerts currently.</p>}
      </div>
    </div>
  );
}

export default App;
