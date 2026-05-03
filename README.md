<div align="center">

# LLM Relay

### Your own AI control room.

**One place to run local AI, connect your tools, manage agents, and keep your data close to home.**

[![Stars](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&color=FFD43B&logo=github)](https://github.com/strikersam/local-llm-server/stargazers)
[![Forks](https://img.shields.io/github/forks/strikersam/local-llm-server?style=for-the-badge&color=4D8CFF&logo=git)](https://github.com/strikersam/local-llm-server/network)
[![License](https://img.shields.io/badge/license-Open%20Source-22C55E?style=for-the-badge)](LICENSE)

[**Quick start**](#quick-start) · [**See the product**](#see-the-product) · [**What it can do**](#what-it-can-do) · [**Technical docs**](#technical-docs)

</div>

---

## What is LLM Relay?

If someone brand new to AI asked, I would say:

> **LLM Relay is a smart front desk for your AI helpers.**
> It knows who is allowed in, which helper should do the job, what it costs, and where everything should go.

In normal people words:

- you can run **AI on your own computer or server**
- you can connect **Cursor, Claude Code, Aider, Continue, scripts, and dashboards** to one place
- you can give your team a **simple web app** to chat, create tasks, manage agents, and watch what is happening
- you can keep control of **costs, access, secrets, and data**

### Why this feels different

Many AI tools solve only one piece of the puzzle.
LLM Relay tries to bring the important pieces together in one product:

- **one place to connect tools** instead of many separate configs
- **one dashboard for people** instead of making everyone live in terminals
- **one set of rules** for cost, access, routing, and safety
- **one shared memory** for chats, tasks, sources, and team knowledge

That means less setup pain, less tool sprawl, and fewer "wait, where did that answer come from?" moments.

<p align="center">
  <img src="docs/screenshots/v3-control-plane.png" alt="LLM Relay control plane" width="100%"/>
  <br/>
  <sub><em>The main control plane: one screen for chat, tasks, agents, models, knowledge, and system health.</em></sub>
</p>

---

## Why people use it

Most teams hit the same problems:

- AI tools are scattered across too many tabs and services
- cloud AI bills grow fast
- local models are powerful, but harder for normal people to use
- one person knows the setup, everyone else is confused
- nobody knows which model, agent, or tool did what

LLM Relay turns that mess into **one home for your AI work**.

### In one glance

| If you want... | LLM Relay gives you... |
|---|---|
| one simple way to use local AI | one URL your tools can all talk to |
| lower cloud spend | local-first and cost-aware routing |
| a team-friendly AI product | chat, tasks, agents, schedules, and knowledge in one place |
| more trust and control | logins, roles, audit trails, secrets, and activity history |
| something that can start small | a setup that works for solo use and grows into a team control plane |

---

## What it can do

### 🧠 1. Run AI from one simple address

Instead of teaching every app a different setup, you point them all at one URL.
That means Cursor, Claude Code, Aider, Continue, scripts, and internal tools can all use the same front door.

### 💸 2. Help you spend less

LLM Relay can prefer **local models first**, then try **free providers**, and only use paid services when needed.
That makes it easier to keep costs under control without asking every user to think about pricing all day.

### 🤖 3. Give you agents, not just chat

You can create agents with different roles.
For example:

- a coding helper
- a reviewer
- a research agent
- a scheduled worker that runs later

### 🗂 4. Turn AI work into visible tasks

Instead of losing everything inside chat messages, you can create tasks, move them across a board, add comments, approve work, retry runs, and see what is blocked.

### 📚 5. Keep team knowledge in one place

LLM Relay includes a wiki and source library so your team can save useful information, project notes, links, and imported material.

### 🛡 6. Control who can do what

It supports API keys, admin login, dashboard login, roles, social login, audit trails, encrypted secrets, and safer shared access for teams.

### 🔭 7. Show you what is happening

You can see activity, routing decisions, usage, savings, logs, health, and observability data instead of guessing whether the system is working.

### 🧰 8. Grow with you

You can start small and still have room for bigger workflows later:

- local models with Ollama
- remote providers like Hugging Face, OpenRouter, DeepSeek, Anthropic, or NVIDIA NIM
- GitHub integration
- schedules and automations
- browser automation
- voice transcription
- Telegram control
- peer sync between machines

### ❤️ Why this can create traction inside a team

Good internal AI tools spread when they are easy to explain.
This one is easy to explain:

- **for leaders:** better visibility and cost control
- **for operators:** better permissions, logs, and safer access
- **for builders:** better model flexibility and automation
- **for everyone else:** a simpler place to just use AI without learning five different systems

---

## See the product

### 🛬 Login

People can sign in through a simple starting page instead of touching raw config files.

<p align="center"><img src="docs/screenshots/v3-login.png" width="92%" alt="LLM Relay login"/></p>

### 🧙 Setup Wizard

The wizard helps you choose providers, models, runtimes, a default agent, and a cost policy.
This is the best path for non-technical users.

<p align="center"><img src="docs/screenshots/v3-setup-wizard.png" width="92%" alt="Setup Wizard"/></p>

### 💬 Chat

This is where people talk to AI directly, using the providers and rules you set up.

<p align="center"><img src="docs/screenshots/v3-chat.png" width="92%" alt="Direct Chat"/></p>

### 🗂 Task Board

This makes AI work visible.
You can see what is waiting, running, blocked, in review, or done.

<p align="center"><img src="docs/screenshots/v3-tasks-kanban.png" width="92%" alt="Kanban Task Board"/></p>

### 🤖 Agent Roster

This is your cast of AI helpers.
Each agent can have its own model, runtime, specialty, and rules.

<p align="center"><img src="docs/screenshots/v3-agents.png" width="92%" alt="Agent Roster"/></p>

### ⚙️ Runtimes

This shows the engines behind the scenes that actually run your AI work.

<p align="center"><img src="docs/screenshots/v3-runtimes.png" width="92%" alt="Agent Runtimes"/></p>

### 🛣 Routing Policy

This is where you decide how smart, cheap, fast, or private the system should be when picking a model.

<p align="center"><img src="docs/screenshots/v3-routing.png" width="92%" alt="Routing Policy"/></p>

### 🔌 Providers and Models

This is where you connect local and cloud AI sources and decide what models are available.

<p align="center">
  <img src="docs/screenshots/v3-providers.png" width="48%" alt="Providers"/>
  &nbsp;
  <img src="docs/screenshots/v3-models.png" width="48%" alt="Models"/>
</p>

### 📚 Knowledge

This is your team's memory: wiki pages, source material, and reusable context.

<p align="center"><img src="docs/screenshots/v3-knowledge.png" width="92%" alt="Knowledge and Wiki"/></p>

### 🔭 Logs and activity

This helps you answer, “what just happened?”

<p align="center"><img src="docs/screenshots/v3-logs.png" width="92%" alt="Logs"/></p>

### 🗓 Schedules

This is how you make AI jobs run later or run again automatically.

<p align="center"><img src="docs/screenshots/v3-schedules.png" width="92%" alt="Schedules"/></p>

### 🛡 Admin portal

This gives admins a simpler place to manage access, controls, and system behavior.

<p align="center"><img src="docs/screenshots/v3-admin.png" width="92%" alt="Admin Portal"/></p>

---

## What kinds of people is this for?

LLM Relay works for:

- **solo builders** who want one clean way to use local AI
- **non-technical teams** who need a dashboard instead of command lines
- **engineering teams** who want routing, agent runs, GitHub workflows, and observability
- **ops/admin owners** who need control, auditability, and safer access
- **cost-conscious companies** who want more local AI and fewer surprise bills

---

## Common use cases

### “I just want local AI to work with my tools.”
Use the proxy and point your tools to it.

### “I want a team dashboard.”
Use the control plane so people can chat, create tasks, manage agents, and see results.

### “I want AI jobs to happen on their own.”
Use schedules, tasks, playbooks, and workflows.

### “I want to mix local and cloud models safely.”
Use routing policies, provider priority, and approval-aware escalation.

### “I want our AI to remember project context.”
Use the wiki, sources, and GitHub integration.

### “I want something I can demo in five minutes.”
Open the control plane, show chat, tasks, agents, routing, and logs, and people quickly understand the value.

---

## Quick start

### Fastest path for most people

> Right now, this repo does **not** include a committed `.env.example`, so create `.env` yourself.

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cat > .env <<'ENV'
API_KEYS=sk-relay-dev
ADMIN_SECRET=replace-with-a-long-random-secret
ADMIN_EMAIL=admin@llmrelay.local
ADMIN_PASSWORD=replace-with-a-strong-password
JWT_SECRET=replace-with-another-long-random-secret
ENV

docker compose up -d
docker compose --profile dashboard up -d
```

Then open:

- **http://localhost:3000** → full control plane
- **http://localhost:8000/admin/ui/login** → built-in admin portal
- **http://localhost:8000/app** → built-in web UI
- **http://localhost:8000/health** → health check

### Pull local models

```bash
docker exec llm-server-ollama ollama pull qwen3-coder:30b
docker exec llm-server-ollama ollama pull deepseek-r1:32b
```

### If you only want the core proxy

```bash
uvicorn proxy:app --reload --port 8000
```

---

## Sign in

### Full control plane (`http://localhost:3000`)

- **Email:** `ADMIN_EMAIL`
- **Password:** `ADMIN_PASSWORD`

### Built-in admin portal (`http://localhost:8000/admin/ui/login`)

- **Username:** anything
- **Password:** `ADMIN_SECRET`

> Pick strong secrets before exposing this outside your machine.

---

## Connect your tools

### Cursor

```text
API Key:                  sk-relay-...
Override OpenAI Base URL: http://localhost:8000/v1
```

### Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
export ANTHROPIC_API_KEY=sk-relay-...
claude
```

### Simple API call

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-relay-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder:30b","messages":[{"role":"user","content":"hello"}]}'
```

If you use Aider, Continue, Zed, VS Code, or Python scripts, examples live in [`client-configs/`](client-configs/).

---

## What is included under the hood?

You do **not** need to learn all of this to get started, but the platform includes:

- OpenAI-style and Anthropic-style API compatibility
- Ollama support
- local + remote model routing
- task boards and schedules
- agent sessions and runtimes
- workflows and approvals
- knowledge wiki and source ingestion
- GitHub repo and pull request flows
- secrets storage
- sync between machines
- observability and cost insights
- hardware detection
- browser and voice tools
- Telegram bot controls

You do not need to learn all of these on day one.
Most people start with **chat + models + one dashboard**, then add the rest when the team is ready.

If you want the deep technical breakdown, jump to the docs below.

---

## Technical docs

For engineers and advanced admins:

- [Feature guide](docs/features.md)
- [API surfaces and route map](docs/api-surfaces.md)
- [Configuration reference](docs/configuration-reference.md)
- [Architecture overview](docs/architecture/overview.md)
- [Model routing guide](docs/model-routing.md)
- [Claude Code setup](docs/claude-code-setup.md)
- [Agent runtime setup](docs/runbooks/agent-runtime-setup.md)
- [Docker agent runtimes](docs/runbooks/docker-agent-runtimes.md)
- [Langfuse observability](docs/langfuse-observability.md)
- [Admin dashboard guide](docs/admin-dashboard.md)
- [Device compatibility](docs/device-compatibility.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Changelog](docs/changelog.md)

---

## A simple way to think about it

LLM Relay is:

- **a front door** for AI requests
- **a switchboard** that picks the right model
- **a control room** for teams
- **a memory box** for saved knowledge
- **a manager** for agents, tasks, and schedules

It is built for people who want AI to feel like **one understandable product**, not a pile of disconnected tools.

If you want AI to feel less like scattered tools and more like one product, that is what this repo is trying to do.

---

## License

Open source. Use it, change it, and make it better.

---

<div align="center">

If LLM Relay helps you, a star helps other people find it.

[![Star this repo](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&logo=github&color=FFD43B)](https://github.com/strikersam/local-llm-server/stargazers)

</div>
