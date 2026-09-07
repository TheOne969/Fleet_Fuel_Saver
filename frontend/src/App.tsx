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
          <div key={i} style={{ padding: '10px', border: '1px solid red', borderRadius: '4px', background: '#fee' }}>
            <strong>{a.trip_id}</strong> - {a.type} (Speed: {a.speed.toFixed(1)}, RPM: {a.rpm}, Z: {a.z_score.toFixed(2)})
          </div>
        ))}
        {alerts.length === 0 && <p>No alerts currently.</p>}
      </div>
    </div>
  );
}

export default App;

