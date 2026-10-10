import type { ActionResponse } from '@/types/hermes'

import { capabilityScoped, type ProfileScope } from './client'

export interface EccWorkflowStatus {
  cursor_hooks: boolean
  home: string
  home_display: string
  install_state_path: string
  installed: boolean
  memory_vault: boolean
  pack_id: string
  profile: string
  skill_count: number
  target: string
  title: string
  version: null | string
}

export function getEccWorkflowStatus(profile?: ProfileScope): Promise<EccWorkflowStatus> {
  return window.hermesDesktop.api<EccWorkflowStatus>({
    ...capabilityScoped(profile),
    path: '/api/workflows/ecc'
  })
}

export function installEccWorkflows(profile?: ProfileScope): Promise<ActionResponse> {
  return window.hermesDesktop.api<ActionResponse>({
    ...capabilityScoped(profile),
    path: '/api/workflows/ecc/install',
    method: 'POST',
    body: {}
  })
}

export function updateEccWorkflows(profile?: ProfileScope): Promise<ActionResponse> {
  return window.hermesDesktop.api<ActionResponse>({
    ...capabilityScoped(profile),
    path: '/api/workflows/ecc/update',
    method: 'POST',
    body: {}
  })
}

export function removeEccWorkflows(profile?: ProfileScope): Promise<ActionResponse> {
  return window.hermesDesktop.api<ActionResponse>({
    ...capabilityScoped(profile),
    path: '/api/workflows/ecc/remove',
    method: 'POST',
    body: {}
  })
}
