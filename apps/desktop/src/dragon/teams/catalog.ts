import { HYPERFRAMES_IDENTIFIER } from '@/lib/dragon-hub-catalog'

/** A bot seat in a marketplace team. Each seat installs as its own bot profile. */
export interface TeamSeat {
  slug: string
  title: string
  role: string
  mission: string
  color: string
  /** The seat drives its own VM desktop (browser, apps) rather than only chatting. */
  computer?: boolean
  /** Skills Hub identifiers installed into this seat's bot profile. */
  skills?: string[]
}

export interface MarketplaceTeam {
  slug: string
  name: string
  tagline: string
  description: string
  category: 'Business' | 'Engineering' | 'Finance' | 'Marketing' | 'Research' | 'Sales' | 'Support'
  accent: string
  seats: TeamSeat[]
  /** Skills mentioned on every seat SOUL as team capabilities (install is per-seat). */
  skills?: string[]
}

export const TEAMS_CATALOG: MarketplaceTeam[] = [
  {
    slug: 'realestate',
    name: 'Real Estate Lead Gen',
    tagline: 'Find motivated sellers, write the listing, keep every lead warm.',
    description:
      'Prospects public records and listing sites from its own desktop, drafts outreach and listing copy, and runs the follow-up cadence so no lead goes cold.',
    category: 'Sales',
    accent: '#d9a441',
    seats: [
      {
        slug: 'scout',
        title: 'Lead Scout',
        role: 'Prospector',
        mission: 'Search listing sites, expired listings, and public records for motivated sellers and log each lead with contact details and a reason to call.',
        color: '#d9a441',
        computer: true
      },
      {
        slug: 'writer',
        title: 'Listing Writer',
        role: 'Copywriter',
        mission:
          'Turn property facts and photos into listing descriptions, open-house flyers, social posts, and short listing videos in the agent’s voice. Use HyperFrames for HTML-to-MP4 listing clips.',
        color: '#c0784a',
        computer: true,
        skills: [HYPERFRAMES_IDENTIFIER]
      },
      {
        slug: 'closer',
        title: 'Follow-up Closer',
        role: 'Nurture',
        mission: 'Run the follow-up schedule for every open lead, draft the next touch, and flag anyone ready for a call.',
        color: '#8c6bd1'
      },
      {
        slug: 'comps',
        title: 'Market Analyst',
        role: 'Comps',
        mission: 'Pull comparable sales for a property and write a one-page pricing brief with a suggested list range.',
        color: '#4f9d8f',
        computer: true
      }
    ]
  },
  {
    slug: 'marketing',
    name: 'Marketing',
    tagline: 'Plan the campaign, write the copy, produce the video, ship it.',
    description:
      'A lead who routes briefs, a writer for long-form, a video producer who renders HTML to MP4 with HyperFrames, and a social manager who adapts each piece for every channel.',
    category: 'Marketing',
    accent: '#e0607e',
    skills: [HYPERFRAMES_IDENTIFIER],
    seats: [
      {
        slug: 'lead',
        title: 'Marketing Lead',
        role: 'Router',
        mission:
          'Own the content calendar, break campaigns into briefs, and hand writing to Content Writer, video to Video Producer (HyperFrames), and channel posts to Social Media Manager.',
        color: '#e0607e'
      },
      {
        slug: 'writer',
        title: 'Content Writer',
        role: 'Writer',
        mission: 'Write blog posts, newsletters, and landing-page copy from a brief, matching the brand voice guide.',
        color: '#d68a4c'
      },
      {
        slug: 'video',
        title: 'Video Producer',
        role: 'Video',
        mission:
          'Turn briefs and HTML compositions into short deterministic MP4s with HyperFrames. Render in this bot’s Linux Computer sandbox (Node 22+, Chromium, ffmpeg). Start from /hyperframes.',
        color: '#c45c9e',
        computer: true,
        skills: [HYPERFRAMES_IDENTIFIER]
      },
      {
        slug: 'social',
        title: 'Social Media Manager',
        role: 'Social',
        mission: 'Adapt each piece — including HyperFrames clips from Video Producer — for every channel, schedule posts, and summarize replies worth answering.',
        color: '#5b8def',
        computer: true
      }
    ]
  },
  {
    slug: 'trading',
    name: 'Trading Team',
    tagline: 'Watch the market, size the risk, keep an honest journal.',
    description:
      'Research and risk seats that watch your symbols, check every idea against your rules, and journal each trade. Research only — it never places orders.',
    category: 'Finance',
    accent: '#3fb68b',
    seats: [
      {
        slug: 'watcher',
        title: 'Market Watcher',
        role: 'Research',
        mission: 'Track the watchlist, news, and earnings dates, and post a morning brief with anything that changed overnight.',
        color: '#3fb68b',
        computer: true
      },
      {
        slug: 'risk',
        title: 'Risk Officer',
        role: 'Risk',
        mission: 'Check each proposed trade against position-size and drawdown rules and say plainly when one breaks them.',
        color: '#e06b5a'
      },
      {
        slug: 'journal',
        title: 'Trade Journal',
        role: 'Analyst',
        mission: 'Log every trade with the thesis and outcome, and write a weekly review of patterns in wins and losses.',
        color: '#7d8bd6'
      }
    ]
  },
  {
    slug: 'engineering',
    name: 'Engineering Pod',
    tagline: 'Plan, build, review, and test with a small dev team.',
    description:
      'A tech lead who scopes the work, a builder with its own desktop and terminal, a reviewer, and a tester who reproduces bugs before anyone fixes them.',
    category: 'Engineering',
    accent: '#6f93cf',
    seats: [
      {
        slug: 'lead',
        title: 'Tech Lead',
        role: 'Planner',
        mission: 'Turn requests into scoped tasks with acceptance criteria and assign them to the builder.',
        color: '#6f93cf'
      },
      {
        slug: 'builder',
        title: 'Builder',
        role: 'Developer',
        mission: 'Implement tasks in the repository, run the tests, and open a change with a clear summary.',
        color: '#4fb0c6',
        computer: true
      },
      {
        slug: 'reviewer',
        title: 'Code Reviewer',
        role: 'Reviewer',
        mission: 'Review each change for correctness, security, and readability, and request specific fixes.',
        color: '#b07ad6'
      },
      {
        slug: 'qa',
        title: 'QA Tester',
        role: 'Tester',
        mission: 'Reproduce reported bugs, write regression tests, and verify fixes in the running app.',
        color: '#d4a64a',
        computer: true
      }
    ]
  },
  {
    slug: 'support',
    name: 'Customer Support',
    tagline: 'Answer the inbox fast and escalate what matters.',
    description:
      'Triage sorts every ticket, the help desk answers from your docs, and escalations writes up the hard cases for a human with full context.',
    category: 'Support',
    accent: '#53a6e0',
    seats: [
      {
        slug: 'triage',
        title: 'Ticket Triage',
        role: 'Router',
        mission: 'Read each incoming ticket, tag urgency and topic, and route it to the help desk or escalations.',
        color: '#53a6e0'
      },
      {
        slug: 'desk',
        title: 'Help Desk',
        role: 'Responder',
        mission: 'Draft replies from the knowledge base and past answers, and note any doc that is missing or wrong.',
        color: '#5fbf8f'
      },
      {
        slug: 'escalations',
        title: 'Escalations',
        role: 'Handoff',
        mission: 'Summarize hard tickets with history, attempted fixes, and a recommended next step for a human.',
        color: '#e08a5a'
      }
    ]
  },
  {
    slug: 'research',
    name: 'Research Desk',
    tagline: 'Deep answers with sources you can check.',
    description:
      'A lead researcher who browses from its own desktop, a fact checker who verifies every claim, and a writer who turns findings into a brief.',
    category: 'Research',
    accent: '#a98be0',
    seats: [
      {
        slug: 'researcher',
        title: 'Lead Researcher',
        role: 'Researcher',
        mission: 'Search, read, and collect sources on a question, keeping quotes and links for every finding.',
        color: '#a98be0',
        computer: true
      },
      {
        slug: 'checker',
        title: 'Fact Checker',
        role: 'Verifier',
        mission: 'Check every claim in a draft against its source and mark anything unsupported.',
        color: '#e0b04f'
      },
      {
        slug: 'brief',
        title: 'Brief Writer',
        role: 'Writer',
        mission: 'Write a one-page brief from verified findings with a summary, key points, and citations.',
        color: '#5aa7a0'
      }
    ]
  }
]

export function seatProfileName(team: MarketplaceTeam, seat: TeamSeat): string {
  return `${team.slug}-${seat.slug}`.slice(0, 64)
}

export function seatSkillIdentifiers(seat: TeamSeat): string[] {
  return [...(seat.skills ?? [])]
}

export function teamInstallPlan(team: MarketplaceTeam): { profile: string; skills: string[]; title: string }[] {
  return team.seats.map(seat => ({
    profile: seatProfileName(team, seat),
    skills: seatSkillIdentifiers(seat),
    title: seat.title
  }))
}

export function seatSoul(team: MarketplaceTeam, seat: TeamSeat): string {
  const teammates = team.seats.filter(other => other.slug !== seat.slug)
  const ownSkills = seatSkillIdentifiers(seat)
  const teamSkills = [...(team.skills ?? [])]

  return [
    `# ${seat.title}`,
    '',
    `**Role:** ${seat.role} on the ${team.name} team.`,
    `**Mission:** ${seat.mission}`,
    '',
    '## Team',
    ...teammates.map(other => `- @${seatProfileName(team, other)}: ${other.title} (${other.role})`),
    teamSkills.length
      ? [
          '',
          '## Team skills',
          ...teamSkills.map(id => `- ${id}`),
          'These skills are available to the team. Video work uses HyperFrames (Apache-2.0, HeyGen) — prefer the Linux Computer sandbox for renders.'
        ].join('\n')
      : '',
    ownSkills.length
      ? [
          '',
          '## Your skills',
          ...ownSkills.map(id => `- ${id}`),
          'Installed into this bot profile. For HyperFrames, run `/hyperframes` then render in the sandbox.'
        ].join('\n')
      : '',
    '',
    'Hand work to a teammate with message_agent when it is theirs to do, and report back to the Chief of Staff when a task is finished or blocked.',
    seat.computer ? '\nYou have your own computer (a VM desktop). Use it to browse and run apps when the task needs it.' : ''
  ]
    .join('\n')
    .trim()
}
