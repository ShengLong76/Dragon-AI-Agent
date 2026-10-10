import { describe, expect, it } from 'vitest'

import { HYPERFRAMES_IDENTIFIER } from '@/lib/dragon-hub-catalog'

import {
  type MarketplaceTeam,
  seatProfileName,
  seatSkillIdentifiers,
  seatSoul,
  teamInstallPlan,
  TEAMS_CATALOG,
  type TeamSeat
} from './catalog'
import { copyNamesFramework } from './workflow-packs'

const REQUIRED_SEAT_KEYS: (keyof TeamSeat)[] = ['slug', 'title', 'role', 'mission', 'color']

const REQUIRED_TEAM_KEYS: (keyof MarketplaceTeam)[] = [
  'slug',
  'name',
  'tagline',
  'description',
  'category',
  'accent',
  'seats'
]

function marketingTeam(): MarketplaceTeam {
  const team = TEAMS_CATALOG.find(entry => entry.slug === 'marketing')

  expect(team).toBeTruthy()

  return team as MarketplaceTeam
}

function realEstateTeam(): MarketplaceTeam {
  const team = TEAMS_CATALOG.find(entry => entry.slug === 'realestate')

  expect(team).toBeTruthy()

  return team as MarketplaceTeam
}

describe('Teams Marketplace catalog schema', () => {
  it('validates every team pack and seat', () => {
    expect(TEAMS_CATALOG.length).toBeGreaterThanOrEqual(2)

    for (const team of TEAMS_CATALOG) {
      for (const key of REQUIRED_TEAM_KEYS) {
        expect(team[key], `${team.slug}.${String(key)}`).toBeTruthy()
      }

      expect(team.seats.length).toBeGreaterThanOrEqual(2)
      expect(new Set(team.seats.map(seat => seat.slug)).size).toBe(team.seats.length)

      if (team.skills) {
        expect(team.skills.every(id => typeof id === 'string' && id.length > 0)).toBe(true)
      }

      for (const seat of team.seats) {
        for (const key of REQUIRED_SEAT_KEYS) {
          expect(seat[key], `${team.slug}/${seat.slug}.${String(key)}`).toBeTruthy()
        }

        if (seat.skills) {
          expect(seat.skills.every(id => typeof id === 'string' && id.length > 0)).toBe(true)
        }

        expect(seatProfileName(team, seat)).toMatch(new RegExp(`^${team.slug}-${seat.slug}`))
      }
    }
  })

  it('never names the upstream framework in team user-facing copy', () => {
    for (const team of TEAMS_CATALOG) {
      for (const line of [team.name, team.tagline, team.description, ...team.seats.flatMap(seat => [seat.title, seat.role, seat.mission])]) {
        expect(copyNamesFramework(line), line).toBe(false)
      }

      for (const seat of team.seats) {
        expect(copyNamesFramework(seatSoul(team, seat)), seat.title).toBe(false)
      }
    }
  })
})

describe('Marketing team pack', () => {
  it('is a small Marketing pack with Lead, Writer, Video Producer, and Social', () => {
    const team = marketingTeam()

    expect(team.name).toBe('Marketing')
    expect(team.category).toBe('Marketing')
    expect(team.skills).toContain(HYPERFRAMES_IDENTIFIER)
    expect(team.seats.map(seat => seat.title)).toEqual([
      'Marketing Lead',
      'Content Writer',
      'Video Producer',
      'Social Media Manager'
    ])

    const video = team.seats.find(seat => seat.slug === 'video')

    expect(video?.computer).toBe(true)
    expect(seatSkillIdentifiers(video as TeamSeat)).toContain(HYPERFRAMES_IDENTIFIER)
    expect(seatSoul(team, video as TeamSeat)).toMatch(/HyperFrames/)
  })

  it('installs HyperFrames on Video Producer and lists it for the team', () => {
    const plan = teamInstallPlan(marketingTeam())
    const video = plan.find(row => row.title === 'Video Producer')

    expect(video?.skills).toEqual([HYPERFRAMES_IDENTIFIER])
    expect(plan.filter(row => row.skills.includes(HYPERFRAMES_IDENTIFIER)).map(row => row.title)).toEqual([
      'Video Producer'
    ])
  })
})

describe('Real Estate Listing Writer', () => {
  it('includes HyperFrames for listing videos', () => {
    const team = realEstateTeam()
    const writer = team.seats.find(seat => seat.slug === 'writer')

    expect(writer?.title).toBe('Listing Writer')
    expect(seatSkillIdentifiers(writer as TeamSeat)).toContain(HYPERFRAMES_IDENTIFIER)
    expect(writer?.computer).toBe(true)
    expect(writer?.mission).toMatch(/listing videos/i)
    expect(teamInstallPlan(team).find(row => row.title === 'Listing Writer')?.skills).toContain(
      HYPERFRAMES_IDENTIFIER
    )
  })
})
