import { useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import type { DropResult } from '@hello-pangea/dnd'
import clsx from 'clsx'
import { ApplicationCard } from './ApplicationCard'
import type { TrackerApplication, ApplicationStatus } from '@/types'

const COLUMNS: { id: ApplicationStatus; label: string; color: string }[] = [
  { id: 'Applied', label: 'Applied', color: 'text-text-secondary' },
  { id: 'Interview', label: 'Interview', color: 'text-accent-primary' },
  { id: 'Offer', label: 'Offer', color: 'text-success' },
  { id: 'Rejected', label: 'Rejected', color: 'text-danger' },
]

interface KanbanBoardProps {
  applications: TrackerApplication[]
  onMoveStatus: (id: string, status: ApplicationStatus) => void
  onDelete: (id: string) => void
}

export function KanbanBoard({ applications, onMoveStatus, onDelete }: KanbanBoardProps) {
  const getAppsForColumn = useCallback(
    (status: ApplicationStatus) =>
      applications.filter((app) => app.status === status),
    [applications]
  )

  const handleDragEnd = useCallback(
    (result: DropResult) => {
      if (!result.destination) return
      const { draggableId } = result
      const newStatus = result.destination.droppableId as ApplicationStatus
      onMoveStatus(draggableId, newStatus)
    },
    [onMoveStatus]
  )

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const columnApps = getAppsForColumn(col.id)
          return (
            <div key={col.id}>
              {/* Column header */}
              <div className="flex items-center justify-between mb-3 px-1">
                <h3 className={clsx('text-sm font-semibold', col.color)}>
                  {col.label}
                </h3>
                <span className="text-xs text-text-muted bg-bg-overlay px-2 py-0.5 rounded-full">
                  {columnApps.length}
                </span>
              </div>

              {/* Droppable column */}
              <Droppable droppableId={col.id}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className={clsx(
                      'min-h-[200px] p-2 rounded-xl border transition-colors',
                      snapshot.isDraggingOver
                        ? 'bg-accent-primary/5 border-accent-primary/20'
                        : 'bg-bg-surface/50 border-white/[0.04]'
                    )}
                  >
                    <AnimatePresence>
                      {columnApps.map((app, index) => (
                        <Draggable key={app.id} draggableId={app.id} index={index}>
                          {(dragProvided) => (
                            <div
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              className="mb-2 last:mb-0"
                            >
                              <ApplicationCard
                                application={app}
                                onDelete={onDelete}
                              />
                            </div>
                          )}
                        </Draggable>
                      ))}
                    </AnimatePresence>
                    {provided.placeholder}

                    {/* Empty state */}
                    {columnApps.length === 0 && !snapshot.isDraggingOver && (
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-xs text-text-muted text-center py-8"
                      >
                        Drag cards here
                      </motion.p>
                    )}
                  </div>
                )}
              </Droppable>
            </div>
          )
        })}
      </div>
    </DragDropContext>
  )
}
