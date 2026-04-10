import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, FileText, X, CheckCircle } from 'lucide-react'
import clsx from 'clsx'
import { formatFileSize } from '@/utils/formatters'

interface ResumeDropzoneProps {
  file: File | null
  onFileChange: (file: File | null) => void
}

export function ResumeDropzone({ file, onFileChange }: ResumeDropzoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles[0]) onFileChange(acceptedFiles[0])
    },
    [onFileChange]
  )

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 5 * 1024 * 1024,
    maxFiles: 1,
  })

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <span className="w-6 h-6 rounded-full bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary text-xs font-bold">
          1
        </span>
        <h2 className="font-display font-semibold text-text-primary">Upload Your Resume</h2>
      </div>

      <AnimatePresence mode="wait">
        {file ? (
          <motion.div
            key="file-preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex-1 flex flex-col items-center justify-center gap-4 bg-bg-elevated border border-success/30 rounded-xl p-8"
          >
            <div className="w-16 h-16 rounded-full bg-success/10 border border-success/30 flex items-center justify-center">
              <CheckCircle size={28} className="text-success" />
            </div>
            <div className="text-center">
              <p className="font-medium text-text-primary mb-1">{file.name}</p>
              <p className="text-sm text-text-muted">{formatFileSize(file.size)}</p>
            </div>
            <button
              onClick={() => onFileChange(null)}
              className="flex items-center gap-1.5 text-sm text-danger hover:text-danger/80 transition-colors"
              aria-label="Remove uploaded file"
            >
              <X size={14} />
              Remove file
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            {...(getRootProps() as Record<string, unknown>)}
            className={clsx(
              'flex-1 flex flex-col items-center justify-center gap-4 rounded-xl p-8 cursor-pointer transition-all duration-300',
              'border-2 border-dashed',
              isDragActive
                ? 'border-accent-primary bg-accent-primary/5 shadow-glow'
                : 'border-contrast/10 bg-bg-elevated hover:border-accent-primary/40 hover:bg-accent-primary/[0.03]'
            )}
          >
            <input {...getInputProps()} aria-label="Resume file upload" />
            <motion.div
              animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
              transition={{ type: 'spring', stiffness: 300 }}
              className={clsx(
                'w-16 h-16 rounded-full flex items-center justify-center',
                isDragActive
                  ? 'bg-accent-primary/20 border border-accent-primary/50'
                  : 'bg-bg-overlay border border-contrast/10'
              )}
            >
              <Upload
                size={24}
                className={isDragActive ? 'text-accent-primary' : 'text-text-muted'}
              />
            </motion.div>

            <div className="text-center">
              <p className="font-medium text-text-primary mb-1">
                {isDragActive ? 'Drop it here!' : 'Drag & drop your resume'}
              </p>
              <p className="text-sm text-text-secondary">
                or <span className="text-accent-primary">click to browse</span>
              </p>
              <p className="text-xs text-text-muted mt-2">PDF or DOCX · Max 5MB</p>
            </div>

            <div className="flex items-center gap-3 text-xs text-text-muted">
              <span className="flex items-center gap-1">
                <FileText size={12} /> PDF
              </span>
              <span className="w-1 h-1 rounded-full bg-text-muted" />
              <span className="flex items-center gap-1">
                <FileText size={12} /> DOCX
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {fileRejections.length > 0 && (
        <p className="mt-2 text-xs text-danger">
          {fileRejections[0].errors[0].message}
        </p>
      )}

      <p className="mt-3 text-xs text-text-muted text-center">
        🔒 Your resume is processed in memory and never stored on our servers.
      </p>
    </div>
  )
}
