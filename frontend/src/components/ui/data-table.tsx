import { useState } from 'react'
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export function DataTable<T>({
  columns,
  data,
  initialSort,
  maxHeight = '560px',
}: {
  columns: ColumnDef<T, unknown>[]
  data: T[]
  initialSort?: SortingState
  maxHeight?: string
}) {
  const [sorting, setSorting] = useState<SortingState>(initialSort ?? [])
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="overflow-auto rounded-[var(--radius-md)] border border-border" style={{ maxHeight }}>
      <table className="w-full border-collapse text-[13px]">
        <thead className="sticky top-0 z-10 bg-surface-2">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => {
                const sortable = header.column.getCanSort()
                const dir = header.column.getIsSorted()
                return (
                  <th
                    key={header.id}
                    onClick={sortable ? header.column.getToggleSortingHandler() : undefined}
                    className={cn(
                      'whitespace-nowrap border-b border-border px-3 py-2.5 text-left font-medium text-ink-2',
                      sortable && 'cursor-pointer select-none hover:text-ink',
                      (header.column.columnDef.meta as { align?: string })?.align === 'right' && 'text-right',
                    )}
                  >
                    <span className="inline-flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortable &&
                        (dir === 'asc' ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : dir === 'desc' ? (
                          <ArrowDown className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-40" />
                        ))}
                    </span>
                  </th>
                )
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b border-border transition-colors last:border-0 hover:bg-surface-2/60">
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  className={cn(
                    'whitespace-nowrap px-3 py-2 text-ink tabnum',
                    (cell.column.columnDef.meta as { align?: string })?.align === 'right' && 'text-right',
                  )}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
