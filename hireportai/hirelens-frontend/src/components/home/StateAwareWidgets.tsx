import { useHomeState } from '@/hooks/useHomeState'
import { StreakAtRiskWidget } from '@/components/home/widgets/StreakAtRiskWidget'
import { MissionActiveWidget } from '@/components/home/widgets/MissionActiveWidget'
import { MissionOverdueWidget } from '@/components/home/widgets/MissionOverdueWidget'
import { ResumeStaleWidget } from '@/components/home/widgets/ResumeStaleWidget'
import { InactiveReturnerWidget } from '@/components/home/widgets/InactiveReturnerWidget'
import { FirstSessionDoneWidget } from '@/components/home/widgets/FirstSessionDoneWidget'
import type { Persona } from '@/context/AuthContext'
import type { HomeStateContext, HomeStateName } from '@/types/homeState'

interface StateAwareWidgetsProps {
  persona: Persona
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
 */
export function StateAwareWidgets({ persona }: StateAwareWidgetsProps) {
  const { data, isLoading, error } = useHomeState()

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
