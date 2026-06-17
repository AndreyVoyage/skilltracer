import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">SkillTracer</h1>
          <p className="text-slate-600 mb-8">Life tracking platform</p>
          <button
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            onClick={() => setCount((count) => count + 1)}
          >
            Count: {count}
          </button>
        </div>
      </div>
    </>
  )
}

export default App
