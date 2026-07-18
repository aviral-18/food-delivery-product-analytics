import { useState } from 'react'
import * as Popover from '@radix-ui/react-popover'
import { Download, FileText, FileSpreadsheet, FileType } from 'lucide-react'
import { api } from '@/lib/api'
import { useFilters } from '@/state/FiltersProvider'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/misc'

const FORMATS = [
  { ext: 'csv', label: 'CSV', icon: FileText },
  { ext: 'xlsx', label: 'Excel', icon: FileSpreadsheet },
  { ext: 'pdf', label: 'PDF', icon: FileType },
]

/** Downloads an authenticated export (blob) for a backend report key. */
export function ExportButton({ report }: { report: string }) {
  const { filters } = useFilters()
  const [busy, setBusy] = useState<string | null>(null)

  async function download(ext: string) {
    setBusy(ext)
    try {
      const res = await api.get(`/exports/${report}.${ext}`, { params: filters, responseType: 'blob' })
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${report}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setBusy(null)
    }
  }

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <Button variant="secondary" size="sm">
          <Download className="h-3.5 w-3.5" /> Export
        </Button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          align="end"
          className="z-50 w-40 rounded-lg border border-border bg-surface p-1 shadow-[var(--shadow)]"
        >
          {FORMATS.map((f) => (
            <button
              key={f.ext}
              onClick={() => download(f.ext)}
              disabled={busy !== null}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-ink hover:bg-surface-2 disabled:opacity-50"
            >
              {busy === f.ext ? <Spinner className="h-3.5 w-3.5" /> : <f.icon className="h-3.5 w-3.5 text-ink-2" />}
              {f.label}
            </button>
          ))}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
