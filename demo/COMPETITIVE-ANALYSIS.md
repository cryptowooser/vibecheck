# vibecheck — Competitive Analysis & Hackathon Positioning

> **Hackathon:** Mistral Worldwide Hackathon (Tokyo, March 1-2, 2026)
> **Track:** API (not Fine-Tuning)
> **Team size:** 2
> **Last updated:** 2026-02-28

---

## Competition Format

### Two Tracks
- **API Track** (us) — build the best project using Mistral models via API. No restrictions on project type.
- **Fine-Tuning Track** — fine-tune a Mistral model; gets up to 20 bonus points. Sponsored by W&B.

### Judging Flow
1. **Local judging** (Sunday ~4pm Tokyo) — local judges pick 1st/2nd/3rd for Tokyo
2. **Public vote** — most-liked project globally gets a finals wildcard
3. **Wild cards** — organizers pick up to 3 extra projects for finals
4. **Global finals** (March 9, YouTube Live) — all city 1st-place winners + public vote + wildcards. Final judges include Mistral VP of Science, HuggingFace transformer maintainer, W&B Alex Vulkar

### Rules
- All projects must be built during the hackathon timeframe
- Teams of 1-4 participants
- Open-source libraries, APIs, and pre-trained models allowed (with credit)
- Code and demos must be submitted before the final deadline
- Must comply with applicable laws, ethical AI practices, and code of conduct
- Mistral, partner, and sponsor APIs used per their ToS

### Prizes We're Targeting

| Prize | Award | Our Fit |
|-------|-------|---------|
| **Local 1st (Tokyo)** | $1,500 cash + $3,000 Mistral credits + 3mo ElevenLabs Pro | Primary target |
| **Local 2nd (Tokyo)** | $1,000 cash + $2,000 Mistral credits | Good fallback if demo is solid but not category-leading |
| **Local 3rd (Tokyo)** | $500 cash + $1,000 Mistral credits | Floor target if execution is partial |
| **Best Use of Mistral Vibe** | Mistral branded AirPods (1 winner globally) | Very strong fit — we ARE a Vibe project |
| **Global Winner** | $10K cash + $15K credits + Mistral hiring opps + Supercell Lab interview ($100K) | Stretch — requires winning Tokyo 1st, then finals |
| **Best Voice Use Case (ElevenLabs)** | $2,000-$6,000 in credits (depends on team size) | Possible if we integrate ElevenLabs TTS alongside Voxtral |
| **Best Video Game Project (Supercell)** | Mistral branded Game Boy + consideration for Supercell AI Innovation Lab ($100K value) | Not our target category |

### Judging Criteria (Official Rubric)

Each criterion is weighted equally at **20%**:

| Criterion | Weight | What It Means | vibecheck Score | Notes |
|-----------|--------|---------------|-----------------|-------|
| **Technicity** | 20% | Technical depth, engineering quality, architecture | **Strong** | In-process AgentLoop hooks, typed event system, WebSocket bridge, multi-session state machine, 4-model orchestration. Deep but not gratuitous. |
| **Creativity** | 20% | Novelty, originality, "never seen this before" factor | **Strong** | Mobile-first agent control is a genuinely novel category. Across 40+ winning hackathon projects in research, nothing similar appeared. The "mission control for your AI fleet" framing is fresh. |
| **Usefulness** | 20% | Does it solve a real problem? Would people actually use it? | **Very Strong** | Every vibe-coder knows this pain — agent blocked, you've walked away. We're building it because we need it. Instant relatability with the room. |
| **Demo** | 20% | Quality of live presentation, "wow" factor, audience engagement | **Very Strong** | Split-screen phone+terminal, live approval during pitch, QR code for audience, Japanese voice input. The demo demos itself. |
| **Track Alignment** | 20% | How well it fits the chosen track/challenge | **Very Strong** | We ARE a Vibe project. Not "we used Vibe to build X" — we extend Vibe itself with mobile control. Deep API-track integration across 4 Mistral models. Strongest possible fit for "Best Use of Mistral Vibe" challenge. |

**Projected composite: 85-90/100** — strongest in Usefulness, Demo, and Track Alignment; solid in Technicity and Creativity.

### Organizer Color Commentary

From Joffrey Thomas (pre-meeting):

> *"Don't try to be too technically impressive. Usually it's not the project that ends up winning. It's not the technical demonstration. It's not a job interview."*

> *"Build a project that if you'd ever come across it on social media, you would be like 'this project is super cool.'"*

> *"Most importantly, have fun."*

> *"How good and fun it is is super important. Try to do something impressive, good, that people will want to use."*

**Translation:** The rubric is evenly balanced, but the organizer's own emphasis skews toward Usefulness + Demo + Creativity ("cool," "fun," "want to use"). Technicity is rewarded but won't win on its own. This is good for us — our strongest axes are exactly the ones the organizer is leaning into.

---

## How vibecheck Stacks Up

### The "Oh That's Awesome" Test

**Scenario:** You're scrolling social media and see a 30-second video of someone approving AI code changes from their phone while walking through Shibuya. Three Vibe agents running simultaneously — one writing tests, one refactoring, one fixing a bug. A push notification pops up, they glance at it, voice-approve in Japanese, and keep walking. The agent continues coding.

That's a "stop scrolling" moment. It's immediately understandable, visually compelling, and makes you want to try it.

### Strength Analysis

#### S1: Solves a Real Problem We Actually Have
Every vibe-coder knows the pain: your agent is blocked waiting for approval, and you've walked away. The hackathon research shows judges consistently reward domain expertise applied to genuine friction (postvisit.ai built by a cardiologist, GuruMitra surveyed 48 real teachers, CrossBeam tackled actual building permits). We're building this because we need it.

#### S2: Strong Fit for "Best Use of Mistral Vibe"
This is a special prize with exactly one global winner. We're not just *using* Vibe — we're extending it with a mobile control layer. We hook directly into `AgentLoop` callbacks, use its typed event system, and showcase Vibe as a serious autonomous coding tool. This is one of our strongest prize fits, but still competitive.

#### S3: Four Mistral Models, Each Doing What It's Best At
Most teams will use 1-2 models. We use four across the Mistral product line:

| Model | Role in vibecheck | Why This Model |
|-------|-------------------|----------------|
| **Devstral 2** | Core Vibe coding agent (the agent being controlled) | Best coding model in the Mistral family |
| **Voxtral Mini** | Push-to-talk voice transcription (JA + EN) | Purpose-built for speech-to-text |
| **Ministral 8B** | Notification copy, urgency classification, tool summaries | Fast, cheap, perfect for micro-tasks |
| **Mistral Large 3** | EN<>JA translation with code preservation + camera/multimodal input | Best quality for nuanced translation; multimodal capabilities for vision features |

This breadth is a natural showcase of the Mistral ecosystem — not forced model usage, but each model in its ideal role.

#### S4: Multi-Session = "Mission Control" Demo
The multi-session story transforms vibecheck from "remote control for an agent" to "mission control for your AI fleet." The demo scenario — three agents running, approve one, check on another, deny a sketchy command on the third — is immediately more impressive and more shareable than a single-agent demo.

#### S5: Japanese-First UX for Tokyo Judges
We're at the Tokyo hackathon. Japanese voice input via Voxtral, inline EN<>JA translation, CJK-aware language detection — this isn't a tacked-on feature, it's core UX. GuruMitra won a 57,000-person hackathon partly by supporting 22+ Indian languages. Locale-aware design resonates with local judges.

#### S6: Live Demo Potential Is Extremely High
The split-screen demo (Vibe terminal on projector + phone screen via scrcpy) with QR code for audience participation is inherently theatrical. Judges and audience can *watch it work in real-time*. The most viral hackathon moments (GibberLink, Conductr) came from showing, not explaining. Approving code from your phone while presenting is a demo that demos itself.

#### S7: The Pitch Writes Itself
> "Like most of you, I've been doing a lot of vibecoding lately. And I got tired of being chained to my terminal while my agents waited for me. So we built vibecheck — mission control for your Vibe agents, right from your phone."

30 seconds. Everyone in the room gets it. The name reinforces the concept. The intensity system (Chill to Ralph) adds personality. The notification copy ("Vibe Check: bash wants to run npm test") is instantly relatable.

#### S8: Mobile-First Agent Control Is Differentiated
Across 40+ winning projects in the research — multi-agent orchestrators, RAG pipelines, healthcare AI, education platforms — mobile-first agent interaction appears uncommon. This gives us a clearer lane than generic chatbot projects.

### Risk Analysis

#### R1: Implementation Timeline Is Tight
L0 (backend scaffold + EC2) is done. But the frontend, bridge integration, voice, push notifications, and translation are all pending. The hackathon is ~2 days. Mitigation: every layer is independently demoable. Even L2 (phone + approve/deny) is a compelling demo without voice or translation.

#### R2: Developer Tools Win Less Often Than Healthcare/Education
The research shows healthcare and education are the two most frequently awarded verticals. Developer tooling is viable (zenith.chat, OrgLens, Voice Root all won) but less common. Mitigation: pitch the *human* story (mobility, accessibility, voice-first) not the "dev tools" story.

#### R3: Vibe Integration May Hit Unexpected Issues
We're hooking into Vibe's internal AgentLoop callbacks. If the API surface doesn't work as expected from our code analysis, we fall back to sidecar mode (tmux + JSONL watching). Less clean, but functional. Mitigation: Option B fallback is documented and ready.

#### R4: Not Multi-Agent in the Strict Sense
The dominant hackathon pattern is 2-6 specialized agents orchestrating together. vibecheck is a control layer for multiple *instances* of a single agent type, not a multi-agent system. For a Mistral hackathon focused on Vibe usage, this framing is fine — but for general AI hackathon judges looking for agent orchestration, we'd need to frame carefully.

---

## Positioning Against Likely Competition

### What Other Teams Will Probably Build

Based on hackathon trends and the prize structure:

| Likely Project Type | Frequency | Our Advantage |
|---------------------|-----------|---------------|
| RAG chatbot / knowledge base | Very common | We're not a chatbot — distinctive |
| Healthcare/education AI | Common | Different category, no overlap |
| Video game with AI (Supercell prize) | Common | Different prize target |
| Fine-tuning showcase (W&B track) | ~50% of teams | We're API track — different judging pool |
| Voice assistant / conversational AI | Some | We use voice as *input to an agent*, not as the product |
| Generic "AI agent that does X" | Common | We're meta — we control agents, not build another one |

### Our Unique Position
vibecheck is differentiated as a **mobile control layer for AI coding agents**. We're not directly competing with most chatbots or RAG apps, though some teams may still overlap with broader "agent copilots."

---

## Special Prize Strategy

The judging criteria confirms two **Worldwide Challenges** as separate prize categories:

### Best Use of Mistral Vibe — PRIMARY SPECIAL TARGET
- **This is our strongest special prize alignment of any team at any city.** We are literally a Vibe companion app.
- Deep integration via AgentLoop hooks (not superficial "we used Vibe to build X")
- Multi-session management of Vibe instances
- Showcases Vibe as a serious autonomous coding tool worth building infrastructure around
- Track Alignment score (20% of main rubric) also benefits from this — double-dipping on the same strength
- **Risk:** Someone builds a Vibe plugin/extension that modifies Vibe itself rather than wrapping it

### Best Voice Use Case — SECONDARY SPECIAL TARGET
- **Full voice loop:** Voxtral STT (input) + ElevenLabs TTS (output) = conversational agent control
- Walkie-talkie mode: hold to speak → agent processes → hear response read aloud
- Japanese TTS via ElevenLabs `eleven_multilingual_v2` (32 languages)
- Voice is a differentiating feature, not the core product — but the loop is compelling
- ElevenLabs best projects lean toward accessibility + voice-first UX (Aphasio, Kisan, Pronunciation Coach) — our mobile voice loop fits that pattern
- **Planned:** L7 stretch adds `POST /api/tts` proxy + auto-read toggle + walkie-talkie UX

### Tilde Architectural Prize — NOT A TARGET
- This prize appears aligned with architectural/model-level modification work in the training-oriented lane.
- vibecheck is an API-track product integration project, so we should not plan around this prize.

---

## Key Takeaways for Demo Day

Mapped to the five 20% criteria:

### Hitting Usefulness (20%)
1. **Lead with the story, not the tech.** "I got tired of being chained to my desk" beats "we built a FastAPI WebSocket bridge." Usefulness is about "would people actually use this?" — the answer has to be obvious within 10 seconds.
2. **Show multi-session.** Having 2-3 agents visible in the session switcher transforms "neat" into "I need this." Judges should think "I want that on my phone."

### Hitting Demo (20%)
3. **Demo on the phone.** The split-screen (terminal + scrcpy phone mirror) makes it real. Approve something live during the pitch — this is the single most important demo moment.
4. **QR code for the audience.** Let people pull up the read-only view on their phones. Participation = memorability. Judges who *experience* the product score Demo higher.
5. **Speak Japanese during the demo.** Voice-approve something in Japanese. Local judges will remember this. Also hits Creativity.

### Hitting Track Alignment (20%)
6. **Name-drop the model diversity.** "Four Mistral models, each doing what it's best at" is a one-liner that signals ecosystem depth and deep Mistral API usage.
7. **Emphasize Vibe integration depth.** Briefly mention "we hook directly into Vibe's AgentLoop callbacks" — positions us for both Track Alignment points and the Best Use of Vibe worldwide challenge.

### Hitting Technicity (20%)
8. **Show, don't lecture.** Don't spend time explaining WebSocket architecture. Instead, show real-time events streaming to the phone — the technical depth is *visible* in the responsiveness. If asked, mention the typed event system and multi-session state machine.

### Hitting Creativity (20%)
9. **Frame the novelty.** "No one has built a mobile control layer for coding agents before." One sentence establishes the creative lane. The "mission control" metaphor and intensity system (Chill to Ralph) reinforce originality.

---

## Summary: Why vibecheck Wins

### Scoring Against the Rubric

| Criterion (20% each) | Our Score | Key Evidence |
|-----------------------|-----------|--------------|
| **Technicity** | 8/10 | AgentLoop hooks, typed events, WebSocket bridge, multi-session state machine, 4-model orchestration |
| **Creativity** | 8/10 | Novel category (mobile agent control), "mission control" framing, intensity system personality |
| **Usefulness** | 9/10 | Solves a real pain point every vibe-coder has, built because we need it, instantly relatable |
| **Demo** | 9/10 | Live phone approval, split-screen, QR audience participation, Japanese voice input, theatrical |
| **Track Alignment** | 9/10 | Deep Vibe integration (not just "used Vibe"), 4 Mistral models in natural roles, strongest fit for Best Use of Vibe challenge |
| **Projected Total** | **86/100** | Strongest on the three axes the organizer emphasizes most |

### Additional Factors

| Factor | Score | Notes |
|--------|-------|-------|
| Tokyo-local advantage | High | Japanese voice, translation, locale-aware UX — resonates with local judges |
| "Best Use of Vibe" fit | Very High | Strongest possible alignment for the worldwide challenge |
| "Best Voice Use Case" fit | Medium | Compelling voice loop, but voice isn't the core product |
| Execution risk | Medium-High | Tight timeline; value depends on stable end-to-end demo |

---

*See also: [RESEARCH-hackathon-winners.md](./RESEARCH-hackathon-winners.md) (hackathon winner analysis), [PLAN.md](./PLAN.md) (execution plan), [README.md](./README.md) (product design)*
