import { StreakAtRiskWidget } from '@/components/home/widgets/StreakAtRiskWidget'
import { MissionActiveWidget } from '@/components/home/widgets/MissionActiveWidget'
import { MissionOverdueWidget } from '@/components/home/widgets/MissionOverdueWidget'
import { ResumeStaleWidget } from '@/components/home/widgets/ResumeStaleWidget'
import { InactiveReturnerWidget } from '@/components/home/widgets/InactiveReturnerWidget'
import { FirstSessionDoneWidget } from '@/components/home/widgets/FirstSessionDoneWidget'
import type { Persona } from '@/context/AuthContext'
import type {
  HomeStateContext,
  HomeStateName,
  HomeStateResponse,
} from '@/types/homeState'

interface StateAwareWidgetsProps {
  persona: Persona
  data: HomeStateResponse | null
  isLoading: boolean
  error: Error | null
}

function _renderWidget(
  state: HomeStateName,
  persona: Persona,
  context: HomeStateContext,
) {
  switch (state) {
    case 'mission_overdue':
      return <MissionOverdueWidget persona={persona} context={context} />
    case 'streak_at_risk':
      return <StreakAtRiskWidget persona={persona} context={context} />
    case 'mission_active':
      return <MissionActiveWidget persona={persona} context={context} />
    case 'resume_stale':
      return <ResumeStaleWidget persona={persona} context={context} />
    case 'inactive_returner':
      return <InactiveReturnerWidget persona={persona} context={context} />
    case 'first_session_done':
      return <FirstSessionDoneWidget persona={persona} context={context} />
    default:
      return null
  }
}

/**
 * Renders the priority-slot widget for the user's top active state. On
 * loading, error, or empty `states[]`, renders nothing — the static S18
 * persona grid stands alone in those cases (spec #40 §7).
 *
 * Spec #61: data is now received as a prop from HomeDashboard rather
 * than fetched here, so HomeDashboard can derive `topState` once and
 * pass it both to this component (for rendering the slot) and to
 * static-grid widgets (for §3 composition suppression).
 */
export function StateAwareWidgets({
  persona,
  data,
  isLoading,
  error,
}: StateAwareWidgetsProps) {
  if (isLoading || error || !data || data.states.length === 0) return null

  const top = data.states[0]
  const widget = _renderWidget(top, persona, data.context)
  if (widget === null) return null

  return (
    <div data-testid="state-aware-slot" className="mb-6">
      {widget}
    </div>
  )
}
