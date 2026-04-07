import { createContext, useContext, useReducer } from 'react'
import type { ReactNode } from 'react'
import type { AnalysisAction, AnalysisState } from '@/types'

const initialState: AnalysisState = {
  isLoading: false,
  error: null,
  result: null,
  resumeFile: null,
  jobDescription: '',
}

function analysisReducer(state: AnalysisState, action: AnalysisAction): AnalysisState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload, error: null }
    case 'SET_ERROR':
      return { ...state, isLoading: false, error: action.payload }
    case 'SET_RESULT':
      return { ...state, isLoading: false, error: null, result: action.payload }
    case 'SET_RESUME_FILE':
      return { ...state, resumeFile: action.payload }
    case 'SET_JD':
      return { ...state, jobDescription: action.payload }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

interface AnalysisContextValue {
  state: AnalysisState
  dispatch: React.Dispatch<AnalysisAction>
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null)

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(analysisReducer, initialState)
  return (
    <AnalysisContext.Provider value={{ state, dispatch }}>
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysisContext(): AnalysisContextValue {
  const ctx = useContext(AnalysisContext)
  if (!ctx) throw new Error('useAnalysisContext must be used within AnalysisProvider')
  return ctx
}
