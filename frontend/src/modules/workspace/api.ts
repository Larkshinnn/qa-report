import { api } from '../../shared/api'

export interface WorkspaceUser {
  account_id: string
  display_name: string
  email: string
  report_dates: string[]
  report_count: number
  activity_count: number
  total_hours: number
  pass_rate: number
  issue_count: number
}

export interface WorkspaceSummary {
  month: string
  hours_target: number
  users: WorkspaceUser[]
}

export const workspaceApi = {
  summary: (month: string): Promise<WorkspaceSummary> =>
    api(`/qa-reports/workspace?${new URLSearchParams({ month })}`),
}
