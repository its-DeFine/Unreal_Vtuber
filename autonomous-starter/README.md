# The System (Self-Improvement Agent)

### 1. Introduction

**1.1. Overview**
"The System" is a digital agent designed to assist users in managing their daily lives, achieving personal goals, and promoting self-improvement through structured task management and gamification. Inspired by concepts like the system in "Solo Leveling," it aims to provide motivation, track progress, and eventually offer deeper insights into user habits and productivity. This initial version (MVP) focuses on core task management and points tracking functionalities implemented as an ElizaOS plugin.

**1.2. Vision**
To create a personalized, intelligent agent that acts as a life coach, helping users break down goals into manageable tasks, stay accountable, build positive habits, and "level up" in their real lives. The long-term vision includes multi-platform integration, behavior monitoring, and proactive assistance, developed transparently as an open-source project.

**1.3. Goals (Overall Product)**

- Provide a robust and flexible task management system.
- Motivate users through a gamified points and potentially leveling system.
- Help users track progress towards their goals.
- Establish a foundational architecture for future expansion into behavior monitoring and system integration.
- Develop the system openly to potentially benefit others.

**1.4. Target Audience**

- **Primary (MVP):** The developer (Shaw Walters) - focused on self-improvement and creating a personalized tool.
- **Secondary (Future):** Individuals seeking a gamified approach to productivity, habit formation, and goal achievement, potentially within the open-source community.

### 2. Goals (MVP - `plugin-todo`)

- Implement core CRUD (Create, Read, Update, Delete/Cancel) functionality for different task types within ElizaOS.
- Establish a basic points system for task completion.
- Implement a reminder system for overdue tasks.
- Provide users with visibility into their tasks and points via an ElizaOS provider.
- Utilize ElizaOS Tasks for persistent storage of to-do items.
- Utilize ElizaOS Entity Components for persistent storage of user points.
- Ensure actions are validated based on context (e.g., active tasks exist) rather than simple string matching.

### 3. Non-Goals (MVP)

- System control features (website blocking).
- Browser extension for behavior monitoring.
- Multi-channel notifications beyond the agent's primary interaction platform (e.g., no SMS via Twilio yet).
- Screen monitoring or analysis.
- Advanced AI-driven behavioral insights or time tracking analysis.
- A visual dashboard or dedicated frontend (interactions are via the ElizaOS agent/chat).
- A formalized "leveling" system beyond raw points accumulation.

### 4. User Personas (MVP)

- **Alex (The Developer):** Tech-savvy individual aiming to optimize personal productivity and track progress on daily habits and long-term goals using a self-built, gamified system integrated into their existing digital workflows (chat via ElizaOS).

### 5. MVP Definition (Current State - `plugin-todo` Implementation)

The MVP consists of the `plugin-todo` for ElizaOS, providing the foundational task and points system.

**5.1. Core Functionality: Task Management**

- Users can interact with the ElizaOS agent to manage their tasks.
- Tasks are stored persistently using the ElizaOS Core Task system (`runtime.createTask`, `runtime.getTasks`, `runtime.updateTask`, `runtime.deleteTask`).
- Tasks are associated with the `roomId` where they were created.

**5.2. Task Types Supported**

- **Daily Recurring Tasks:**
  - Identified by `daily` tag.
  - Metadata includes `streak` counter (incremented on completion).
  - Reset daily (via `RESET_DAILY_TASKS` worker) by removing the `completed` tag.
  - Can have optional `recurring-daily`, `recurring-weekly`, etc., tags via `CREATE_TODO`.
- **One-off Tasks:**
  - Identified by `one-off` tag.
  - Can have an optional `dueDate` (ISO string) in metadata.
  - Can have an optional `priority` (1-4) via `priority-X` tag.
  - Can have an optional `urgent` tag.
- **Aspirational Goals:**
  - Identified by `aspirational` tag.
  - Typically no due date, simpler structure.

**5.3. Actions Implemented**

- **`CREATE_TODO` (`actions/createTodo.ts`):**
  - Uses LLM (`extractTodoInfo`) to parse task details (name, description, type, priority, urgency, dueDate) from user message.
  - Handles defaults (e.g., priority 3 for one-off).
  - Initiates a confirmation flow using `AWAITING_CHOICE` task (`CONFIRM_TODO_CREATION`) presented via the bootstrap `choiceProvider` and handled by `choiceAction`.
  - On confirmation (received via `options` in a subsequent handler call), creates the task using `runtime.createTask` with appropriate tags and metadata.
  - Validation: Always `true` (intent determined by handler).
- **`COMPLETE_TODO` (`actions/completeTodo.ts`):**
  - Uses LLM (`extractTaskCompletion`) to identify the task to complete from available active tasks.
  - Handles completion differently based on task type:
    - **Daily:** Increments `streak`, adds `completed` tag (removed by daily reset worker), awards points (base + streak bonus).
    - **One-off:** Checks `dueDate` for on-time/late status, adds `completed` tag, awards points based on status/priority/urgency.
    - **Aspirational:** Awards fixed points, adds `completed` tag.
  - Uses `runtime.updateTask` to modify tags/metadata.
  - Integrates with `pointsService.addPoints`.
  - Validation: Requires active (non-completed) `todo` tasks in the room.
- **`UPDATE_TODO` (`actions/updateTodo.ts`):**
  - Uses LLM (`extractTaskSelection`) to identify the task to update.
  - Uses LLM (`extractTaskUpdate`) to parse desired changes (name, description, priority, urgent, dueDate, recurring).
  - Initiates a confirmation flow using `AWAITING_CHOICE` task (`CONFIRM_TODO_UPDATE`).
  - On confirmation, applies changes using `runtime.updateTask`.
  - Validation: Requires active (non-completed) `todo` tasks in the room.
- **`CANCEL_TODO` (`actions/cancelTodo.ts`):**
  - Uses LLM (`extractTaskCancellation`) to identify the task to cancel.
  - Initiates a confirmation flow using `AWAITING_CHOICE` task (`CONFIRM_TODO_CANCELLATION`).
  - On confirmation, deletes the task using `runtime.deleteTask`.
  - Validation: Requires active (non-completed) `todo` tasks in the room.

**5.4. Points System (`pointsService.ts`)**

- Stores user points in an Entity Component (`userPoints`). Creates component if it doesn't exist.
  - _Caveat:_ Uses placeholder UUIDs for `roomId`/`worldId` during creation, needs refinement for proper context association.
- `calculatePoints`: Provides logic for point values based on task type, priority, urgency, on-time status, and streak.
- `addPoints`: Updates the user's point total and maintains a short history.
- `getPoints`: Retrieves the current point total.

**5.5. Reminders (`reminderService.ts`)**

- Runs as an ElizaOS Service.
- Periodically (hourly) checks for `one-off` tasks where `dueDate` is in the past.
- Sends a reminder message to the task's `roomId` if overdue and a reminder hasn't been sent within the `REMINDER_COOLDOWN` (24 hours).
- Updates task metadata (`lastReminderSent`) after sending.

**5.6. Data Display (`providers/todos.ts`)**

- `TODOS` provider fetches active tasks (`runtime.getTasks`) and user points (`getPoints`).
- Categorizes tasks (Daily, One-off, Aspirational, Recently Completed).
- Formats the information into a text block for the agent's context.
- _Caveat:_ Contains minor, unresolved linter warnings regarding date type checking.

**5.7. Technical Implementation**

- Implemented as an ElizaOS `Plugin` (`plugin-todo`).
- Leverages `@elizaos/core` for runtime, tasks, actions, providers, services, components.
- Uses `zod` for potential configuration validation (though not heavily used in MVP).
- Relies on `bootstrapPlugin` for handling `AWAITING_CHOICE` tasks via `choiceProvider` and `choiceAction`.

### 6. Future Roadmap

**6.1. MVP+1 (Near-Term Enhancements)**

- **Refined Points/Leveling:**
  - Define concrete point values for all scenarios.
  - Implement a basic leveling system based on points thresholds (stored in `userPoints` component).
  - Display level in `TODOS` provider.
- **Enhanced Reminders:**
  - Allow configuration of reminder frequency/timing.
  - Integrate with Discord service to send DMs or pings for reminders.
  - Add ability to "snooze" tasks/reminders.
- **Daily Task Reset Robustness:**
  - Ensure the `RESET_DAILY_TASKS` worker handles different timezones or runs reliably at the user's local start-of-day. Consider making interval configurable.
- **Improved Points Component Context:** Resolve the placeholder UUID issue in `pointsService` by associating the component with the user's primary World or a designated global context.
- **Basic Reporting:** Enhance `TODOS` provider or add a new action to show point history, completion stats over time (e.g., last 30 days).
- **Task Querying:** Add action(s) to query/search tasks (e.g., "show my urgent tasks", "what's due this week?").

**6.2. Phase 2 (Medium-Term Features)**

- **Multi-Channel Reminders:**
  - Integrate Twilio Plugin for SMS reminders (requires Twilio setup/secrets).
- **Chrome Extension (Monitoring - Phase 1):**
  - Develop a simple Chrome extension to track active tab URL and time spent.
  - Send basic browsing data (domain, time) securely to a dedicated API endpoint exposed by the ElizaOS agent (requires adding a route to the plugin).
  - Store this data (e.g., as custom memories or dedicated components).
  - _Security/Privacy:_ Requires explicit user installation and consent. Data transmission must be secure. Start with non-sensitive data (e.g., domains, not full URLs).
- **Basic Time Tracking Analysis:**
  - New provider/action to summarize time spent on tracked websites (from Chrome extension data).
  - Potentially link tasks to website usage (e.g., "Did I spend time on researchgate.net for my 'Write Report' task?").

**6.3. Phase 3 (Long-Term Vision)**

- **System Integration (Website Blocking):**
  - Requires OS-level integration or a more sophisticated browser extension with blocking capabilities.
  - Agent Action (`BLOCK_WEBSITE`) triggers the blocking mechanism.
  - Logic for conditional blocking (e.g., "Block Twitter until daily tasks are done").
  - _Complexity/Risk:_ High. Significant security, privacy, and cross-platform compatibility challenges. Needs careful design and robust implementation. Requires user trust and clear consent.
- **Screen Monitoring & Analysis:**
  - Agent action to trigger screen capture.
  - Secure transmission of screenshot to agent backend.
  - Integration with Vision models (`ModelType.IMAGE_DESCRIPTION`) to describe screen content.
  - Store descriptions as memories associated with user activity.
  - _Complexity/Risk:_ Very High. Extreme privacy implications. Performance intensive. Requires robust security and explicit, granular user consent for each capture.
- **Advanced Behavioral Insights:**
  - Use LLMs to analyze combined task completion data, time tracking data, and potentially screen analysis data.
  - Provide insights like "You tend to get distracted by news sites when working on 'Project X'".
  - Proactive suggestions based on patterns.

### 7. Technical Considerations

- **Architecture:** ElizaOS plugin architecture provides good modularity for MVP. Future features like the Chrome extension and system integration will require separate components communicating with the ElizaOS agent via APIs.
- **Data Storage:**
  - MVP: Core Tasks and Entity Components are sufficient.
  - Future: May need dedicated database tables or structures for time tracking, behavior logs, etc., if component storage becomes inefficient. Consider performance implications of querying large numbers of tasks/components.
- **Security & Privacy:** Paramount for features involving monitoring or system control. Requires:
  - Explicit user consent for all monitoring/control features.
  - Secure data transmission (HTTPS).
  - Secure storage of sensitive data.
  - Transparency about what data is collected and how it's used.
  - Careful permission handling for system control actions.
- **Scalability:** Currently single-user focused. Open-sourcing requires considering multi-tenant database design, resource isolation, and robust error handling if adopted by others.
- **Platform Compatibility:** System control and deep browser integration are highly OS/browser-dependent. Focus initially on specific target platforms (e.g., macOS/Chrome).

### 8. Open Questions & Risks

- How to reliably determine the correct `worldId`/`roomId` for the global `userPoints` component?
- How robust is the bootstrap `choiceAction` interaction for confirmation flows? Needs testing.
- How to securely implement system control features without creating vulnerabilities?
- How to handle the significant privacy implications of behavior/screen monitoring ethically and technically?
- What is the best way to model the "leveling" aspect beyond simple points?
- How to manage the complexity and potential performance impact of analyzing large amounts of user activity data in later phases?
- Cross-platform consistency for reminders and system integrations.

### 9. Success Metrics (MVP)

- User (developer) can successfully create, view, update, complete, and cancel tasks of all defined types via the agent.
- Points are correctly calculated and awarded upon task completion.
- `TODOS` provider accurately reflects current tasks and points.
- `TodoReminderService` successfully sends reminders for overdue one-off tasks.
- Action validation prevents actions from being offered in incorrect contexts (e.g., completing a non-existent task).

### 10. Release Criteria (MVP)

- All features defined in Section 5 (MVP Definition) are implemented in the `plugin-todo`.
- Core functionality is tested (manual testing via agent interaction is acceptable for MVP).
- Linter errors (excluding persistent ones in `providers/todos.ts`) are resolved.
- Documentation (this PRD, README updates) reflects the MVP state.

---

TODO

```
Onboarding

What is the user's name?
Age?
Weight?
Height?
When does the user wake up?
When do they go to sleep

Things to fix

22:12 (7 minutes ago) [ee8e45fe-c55f-0557-aebd-50828d849342] user: hey whats up
-> shorten to the first section of uuid

check composeState structure and document since its confusing
composeState should probably include all non-dynamic providers, seems to not (at least in bootstrap)
```

### You can get the game from here:
 https://github.com/snorkelingcode/UE_Neurosync_Agent
