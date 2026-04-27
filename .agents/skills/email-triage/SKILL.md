# Skill: Email Triage

## Purpose
Rapidly process a backlog of emails by categorizing, prioritizing, and drafting responses or actions. Reduces inbox overwhelm and ensures nothing important is missed.

## When to Use
- Inbox has grown unmanageable
- Returning from time away (vacation, sick leave, conference)
- Daily morning email processing routine
- Before an important deadline to clear blockers

## Instructions

### Step 1: Intake
Accept the email list in any format:
- Paste raw email subjects + senders
- Paste full email bodies
- Describe the emails in natural language

### Step 2: Triage Categories
Assign each email to exactly one category:

| Category | Meaning | Action |
|----------|---------|--------|
| 🔴 **Respond Now** | Urgent, requires your action today | Draft reply |
| 🟡 **Respond Soon** | Important, deadline within the week | Queue for reply |
| 📋 **Action Required** | No reply needed, but triggers a task | Add to task list |
| 📖 **Read Later** | FYI, informational only | Archive after reading |
| 🗑️ **Delete/Archive** | Noise, marketing, irrelevant | Delete immediately |

### Step 3: Draft Responses
For each **Respond Now** and **Respond Soon** email:
- Identify the core ask
- Draft a concise reply (3–5 sentences unless detail is required)
- Flag any information you need before sending

### Step 4: Extract Tasks
For **Action Required** emails, extract concrete tasks:
```
- [ ] [Task from email] — From: [Sender] — Due: [Date if mentioned]
```

### Step 5: Produce Triage Report
```markdown
## Email Triage — [Date]

### 🔴 Respond Now ([count])
**From:** [Sender] | **Subject:** [Subject]
**Draft:**
> [Draft reply text]

---

### 🟡 Respond Soon ([count])
...

### 📋 Tasks Extracted ([count])
- [ ] [Task] — [Source email]

### 📖 Read Later ([count])
- [Subject] from [Sender]

### 🗑️ Archived/Deleted ([count])
- [Subject] — [Reason]
```

## Example Prompt to Trigger
```
/email-triage
Here are my unread emails: [paste list or descriptions]
```

## Output Format
- Triage report in structured markdown
- Draft replies inline for urgent emails
- Task list extracted and ready to copy
- Summary count per category

## Notes
- Never assume you have context the user hasn't provided — ask if reply requires knowledge you don't have
- Keep draft replies professional and concise by default
- Flag emails that seem like phishing or spam
- Preserve sender names and subjects accurately
- If asked to integrate with the repo, save triage reports to `docs/triage/email-YYYY-MM-DD.md`
