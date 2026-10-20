import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { downloadStatement } from './api'

function currentMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default function StatementDownload() {
  const [month, setMonth] = useState(currentMonth())
  const download = useMutation({ mutationFn: () => downloadStatement(month) })

  return (
    <div className="card statement">
      <label htmlFor="statement-month">Monthly statement</label>
      <input
        id="statement-month"
        type="month"
        value={month}
        onChange={(e) => setMonth(e.target.value)}
      />
      <button
        type="button"
        className="btn btn-secondary"
        disabled={download.isPending || month === ''}
        onClick={() => download.mutate()}
      >
        {download.isPending ? 'Preparing...' : 'Download CSV'}
      </button>
      {download.isError && (
        <p role="alert" className="error">
          {download.error.message}
        </p>
      )}
    </div>
  )
}
