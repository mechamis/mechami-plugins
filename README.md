# Mechami Plugins

## The *Finance Tutor* Skill

*A skill/plugin for Claude Code, Claude CoWork, and other AI Agents that support the [Agent Skills standard](https://agentskills.io). Currently, supported platforms include Claude Code and Claude CoWork. Compatibility with OpenAI Codex and additional platforms is in development.*

You want to improve your financial knowledge and literacy, and you’ve got questions. You want to be a more educated consumer and have topics you want to research. The `finance-tutor` skill is here to help. 

Ask questions on topics you want to learn more about, and you'll get educational answers with links to authoritative references. The Q&A session is logged in your working directory for your reference. When you're ready, you can request a compiled report with the information you have covered, including linked footnotes you can use to continue learning and verify information.

> ⚠️ FOR EDUCATIONAL PURPOSES ONLY. This skill does not provide personalized financial advice. All answers are intended for learning and general understanding only. For decisions involving your specific financial situation, consult a licensed financial advisor.

### The Process

- Pick a new working folder to start a new learning session
- Activate the skill by entering `/finance-tutor` **(👉 You must trigger this skill manually)**
- Ask a question: 
    > *"Why do bond prices go down when interest rates go up?"*
- When your question is answered, the Q&A is saved to the `transcript.md` file for your reference. Links to relevant online references are included, so you can verify the information provided and learn more.
    - Your specific prompt is also saved to `prompt_log.md`. This makes it easy to keep track of the history of your research and learning.
- Ask follow-up questions: 
    > *"Why are basis points used for certain financial numbers such as changes in rates?"*
- The transcript and prompt log are updated as you continue
- Ready to wrap up? Ask for a report with everything you covered by prompting: `generate report`
    - A complete `report.md` file with footnotes is generated for your reference and further study
- Review links in your report to verify sources and keep learning more
- End your tutoring session by prompting: `end session`
- You can continue working to study your topic further: come back to your working folder to start a new session
- ... Or start a new research topic in a separate folder

### The Result

- You’re more informed on your finance topic of choice.
- You can research more efficiently.
- You can be more prepared to talk to a licensed professional.
- You’re ready to explore more on your next finance topic.

### Install Steps

#### Claude Code

```
claude plugin marketplace add mechamis/mechami-plugins && 
claude plugin install finance-tutor@mechami-plugins
```

#### Claude CoWork

Add the `mechamis/mechami-plugins` marketplace under `Settings > Plugins`

#### Codex, etc.

Coming soon...

----

&copy; 2026 Mechami Solutions LLC
